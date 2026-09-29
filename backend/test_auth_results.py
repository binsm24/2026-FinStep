"""HTTP integration and real JWT signature verification, without contacting Google."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt
from google.auth.exceptions import TransportError
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Diagnosis, LoginChallenge, LoginSession, User, get_engine
from main import app
from services import multi_stage_service as sim
from services.auth_service import SESSION_COOKIE, CHALLENGE_COOKIE, token_hash

HEADERS = {'Origin': 'http://localhost:5173', 'X-FinStep-Request': '1'}
CLIENT_ID = 'finstep-test.apps.googleusercontent.com'


class AuthResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        cls.signer = crypt.RSASigner.from_string(private, key_id='test-key')
        cls.certs = json.dumps({'test-key': public}).encode()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': f"sqlite:///{(Path(self.temp.name) / 'test.db').as_posix()}",
            'GOOGLE_CLIENT_ID': CLIENT_ID, 'COOKIE_SECURE': 'false',
            'FRONTEND_ORIGINS': HEADERS['Origin'],
        })
        self.env.start()
        get_engine.cache_clear()
        self.clients = []
        self.a = self.client()
        self.b = self.client()
        self.transport = patch('services.auth_service.GoogleRequest', return_value=lambda *a, **kw: SimpleNamespace(status=200, data=self.certs))
        self.transport.start()

    def tearDown(self):
        self.transport.stop()
        for client in self.clients:
            client.__exit__(None, None, None)
        get_engine().dispose()
        get_engine.cache_clear()
        self.env.stop()
        self.temp.cleanup()

    def client(self):
        client = TestClient(app, headers=HEADERS)
        client.__enter__()
        self.clients.append(client)
        return client

    def credential(self, client, subject='google-user-a', **overrides):
        response = client.post('/api/auth/challenge')
        self.assertEqual(response.status_code, 200)
        now = int(time.time())
        claims = {'iss': 'https://accounts.google.com', 'aud': CLIENT_ID, 'sub': subject,
                  'email': f'{subject}@example.com', 'email_verified': True, 'name': '테스트 사용자',
                  'nonce': response.json()['nonce'], 'iat': now - 1, 'exp': now + 600}
        claims.update(overrides)
        return jwt.encode(self.signer, claims).decode()

    def login(self, client, subject='google-user-a', **overrides):
        token = self.credential(client, subject, **overrides)
        return client.post('/api/auth/google', json={'credential': token})

    def finish(self, client):
        started = client.post('/api/multi-stage/voice-phishing/start')
        self.assertEqual(started.status_code, 200)
        sid = started.json()['session_id']
        with patch.object(sim, 'analyze_answer_with_llm', return_value={'llm_available': False}):
            finished = client.post('/api/multi-stage/respond', json={'session_id': sid, 'answer': '전화를 끊는다'})
        self.assertEqual(finished.status_code, 200)
        self.assertTrue(finished.json()['is_finished'])
        return sid

    def test_configuration_missing_is_visible_and_no_fake_login(self):
        with patch.dict(os.environ, {'GOOGLE_CLIENT_ID': ''}):
            self.assertFalse(self.a.get('/api/auth/me').json()['google_configured'])
            self.assertEqual(self.a.post('/api/auth/challenge').status_code, 503)
            self.assertEqual(self.a.post('/api/auth/google', json={'credential': 'fake'}).status_code, 401)

    def test_real_signed_token_creates_session_and_cookie_is_http_only(self):
        response = self.login(self.a)
        self.assertEqual(response.status_code, 200, response.text)
        cookie = response.headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=lax', cookie)
        self.assertEqual(self.a.get('/api/auth/me').json()['user']['id'], response.json()['user']['id'])
        self.assertIn('no-store', self.a.get('/api/auth/me').headers['cache-control'])
        with Session(get_engine()) as db:
            stored = db.scalar(select(LoginSession))
            self.assertEqual(stored.token_hash, token_hash(self.a.cookies[SESSION_COOKIE]))
            self.assertNotEqual(stored.token_hash, self.a.cookies[SESSION_COOKIE])

    def test_invalid_token_claims_rejected(self):
        for claims in [{'aud': 'another-app'}, {'iss': 'https://attacker.invalid'}, {'exp': int(time.time()) - 30},
                       {'nonce': 'wrong'}, {'email_verified': False}, {'sub': ''}]:
            with self.subTest(claims=claims):
                response = self.login(self.a, **claims)
                self.assertEqual(response.status_code, 401, response.text)
                self.assertIsNone(self.a.get('/api/auth/me').json()['user'])

    def test_forged_signature_rejected(self):
        token = self.credential(self.a)
        header, payload, signature = token.split('.')
        signature = ('A' if signature[0] != 'A' else 'B') + signature[1:]
        response = self.a.post('/api/auth/google', json={'credential': '.'.join([header, payload, signature])})
        self.assertEqual(response.status_code, 401)

    def test_challenge_cookie_required_and_token_cannot_be_replayed(self):
        token = self.credential(self.a)
        challenge = self.a.cookies[CHALLENGE_COOKIE]
        self.assertEqual(self.b.post('/api/auth/google', json={'credential': token}).status_code, 401)
        self.assertEqual(self.a.post('/api/auth/google', json={'credential': token}).status_code, 200)
        replay = self.a.post('/api/auth/google', json={'credential': token}, headers={'Cookie': f'{CHALLENGE_COOKIE}={challenge}'})
        self.assertEqual(replay.status_code, 401)

    def test_expired_challenge_and_google_transport_failure(self):
        token = self.credential(self.a)
        with patch('services.auth_service.id_token.verify_oauth2_token', side_effect=TransportError('offline')):
            self.assertEqual(self.a.post('/api/auth/google', json={'credential': token}).status_code, 503)
        with Session(get_engine()) as db:
            db.scalar(select(LoginChallenge)).expires_at = 0
            db.commit()
        self.assertEqual(self.a.post('/api/auth/google', json={'credential': token}).status_code, 401)

    def test_write_origin_and_custom_header_are_required(self):
        client = TestClient(app)
        for headers in [{}, {'Origin': HEADERS['Origin']}, {**HEADERS, 'Origin': 'https://attacker.invalid'}]:
            self.assertEqual(client.post('/api/auth/challenge', headers=headers).status_code, 403)
            self.assertEqual(client.post('/api/auth/logout', headers=headers).status_code, 403)

    def test_identity_uses_sub_not_email(self):
        first = self.login(self.a, email='same@example.com').json()['user']['id']
        again = self.login(self.a, email='new@example.com').json()['user']['id']
        other = self.login(self.b, 'google-user-b', email='same@example.com').json()['user']['id']
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)

    def test_session_expiry_logout_and_rotation(self):
        self.login(self.a)
        old = self.a.cookies[SESSION_COOKIE]
        self.login(self.a)
        with Session(get_engine()) as db:
            self.assertIsNone(db.get(LoginSession, token_hash(old)))
            active = db.get(LoginSession, token_hash(self.a.cookies[SESSION_COOKIE]))
            active.expires_at = 0
            db.commit()
        self.assertEqual(self.a.get('/api/results').status_code, 401)
        self.login(self.a)
        current = self.a.cookies[SESSION_COOKIE]
        self.assertEqual(self.a.post('/api/auth/logout').status_code, 200)
        self.assertIsNone(self.a.get('/api/auth/me').json()['user'])
        with Session(get_engine()) as db:
            self.assertIsNone(db.get(LoginSession, token_hash(current)))

    def test_unauthenticated_archive_rejected_and_guest_sessions_are_private(self):
        sid = self.finish(self.a)
        self.assertEqual(self.a.get('/api/results').status_code, 401)
        self.assertEqual(self.a.post('/api/results', json={'session_id': sid}).status_code, 401)
        self.assertEqual(self.b.get(f'/api/multi-stage/sessions/{sid}/result').status_code, 404)
        self.assertEqual(self.b.post('/api/multi-stage/respond', json={'session_id': sid, 'answer': '다른 답변'}).status_code, 404)

    def test_result_is_saved_once_and_other_account_cannot_read_or_claim(self):
        self.login(self.a)
        self.login(self.b, 'google-user-b')
        sid = self.finish(self.a)
        saved = self.a.post('/api/results', json={'session_id': sid, 'score': 9999, 'user_id': 'attacker'})
        self.assertEqual(saved.status_code, 200, saved.text)
        result_id = saved.json()['id']
        self.assertEqual(self.a.post('/api/results', json={'session_id': sid}).json()['id'], result_id)
        listing = self.a.get('/api/results').json()
        self.assertEqual(len(listing['items']), 1)
        self.assertFalse(listing['has_more'])
        self.assertEqual(self.b.get('/api/results').json()['items'], [])
        self.assertEqual(self.b.get(f'/api/results/{result_id}').status_code, 404)
        self.assertEqual(self.b.post('/api/results', json={'session_id': sid}).status_code, 404)
        self.assertEqual(self.b.get(f'/api/multi-stage/sessions/{sid}/result').status_code, 404)
        report = self.a.get(f'/api/results/{result_id}').json()['result']
        self.assertNotEqual(report['score'], 9999)
        self.assertEqual(report['ending_type'], 'safe_exit')
        self.assertTrue(report['conversation_history'])

    def test_guest_report_can_be_claimed_only_by_original_browser(self):
        sid = self.finish(self.a)
        self.login(self.b, 'google-user-b')
        self.assertEqual(self.b.post('/api/results', json={'session_id': sid}).status_code, 404)
        self.login(self.a)
        self.assertEqual(self.a.post('/api/results', json={'session_id': sid}).status_code, 200)
        self.a.post('/api/auth/logout')
        self.assertEqual(self.a.get(f'/api/multi-stage/sessions/{sid}/result').status_code, 404)

    def test_unfinished_report_rejected(self):
        self.login(self.a)
        sid = self.a.post('/api/multi-stage/voice-phishing/start').json()['session_id']
        self.assertEqual(self.a.post('/api/results', json={'session_id': sid}).status_code, 409)

    def test_saved_reports_and_login_survive_new_database_connection(self):
        user_id = self.login(self.a).json()['user']['id']
        sid = self.finish(self.a)
        result_id = self.a.post('/api/results', json={'session_id': sid}).json()['id']
        get_engine().dispose()
        get_engine.cache_clear()
        self.assertEqual(self.a.get('/api/auth/me').json()['user']['id'], user_id)
        self.assertEqual(self.a.get(f'/api/results/{result_id}').status_code, 200)

    def test_pagination_and_owner_filter(self):
        user_id = self.login(self.a).json()['user']['id']
        with Session(get_engine()) as db:
            for i in range(3):
                db.add(Diagnosis(user_id=user_id, simulation_id=f'page-{i}', scenario_title='테스트', risk_label='안전', created_at=i, snapshot='{}'))
            db.commit()
        first = self.a.get('/api/results?limit=2').json()
        second = self.a.get('/api/results?limit=2&offset=2').json()
        self.assertTrue(first['has_more'])
        self.assertFalse(second['has_more'])
        self.assertEqual(len(first['items']) + len(second['items']), 3)
        self.assertEqual(self.a.get('/api/results?limit=101').status_code, 422)


if __name__ == '__main__':
    unittest.main()
