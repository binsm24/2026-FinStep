import hashlib
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from database import LoginSession, User, get_db
from settings import allowed_origins, google_client_id, secure_cookies

SESSION_COOKIE = 'finstep_session'
GUEST_COOKIE = 'finstep_guest'
CHALLENGE_COOKIE = 'finstep_login_challenge'
SESSION_SECONDS = 60 * 60 * 24 * 7
CHALLENGE_SECONDS = 60 * 10


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def set_cookie(response: Response, name, value, max_age):
    response.set_cookie(name, value, max_age=max_age, httponly=True,
                        secure=secure_cookies(), samesite='lax', path='/')


def trusted_write(request: Request):
    # The SPA sends JSON with a custom header; never accept form/login CSRF.
    if request.headers.get('origin') not in allowed_origins() or request.headers.get('x-finstep-request') != '1':
        raise HTTPException(403, '허용되지 않은 요청입니다.')


def optional_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = db.get(LoginSession, token_hash(token))
    if session is None or session.expires_at <= int(time.time()):
        return None
    return db.get(User, session.user_id)


def require_user(user: User | None = Depends(optional_user)):
    if user is None:
        raise HTTPException(401, '로그인이 필요합니다.')
    return user


def user_info(user):
    return {'id': user.id, 'name': user.name, 'email': user.email} if user else None


def new_simulation_owner(request, response, user):
    if user:
        return 'user:' + user.id
    guest = request.cookies.get(GUEST_COOKIE)
    if not guest or len(guest) != 43:
        guest = secrets.token_urlsafe(32)
        set_cookie(response, GUEST_COOKIE, guest, SESSION_SECONDS)
    return 'guest:' + token_hash(guest)


def check_simulation_owner(session_id, request, user):
    from services.session_store import get_session
    session = get_session(session_id)
    candidates = {'user:' + user.id} if user else set()
    guest = request.cookies.get(GUEST_COOKIE)
    if guest:
        candidates.add('guest:' + token_hash(guest))
    if session is None or session.get('owner') not in candidates:
        raise HTTPException(404, '접근할 수 있는 시뮬레이션이 없습니다.')
    return session


def verify_google_credential(credential):
    client_id = google_client_id()
    if not client_id:
        raise HTTPException(503, '구글 로그인이 아직 준비되지 않았습니다.')
    try:
        # google-auth verifies signature, audience, expiration and Google issuer.
        claims = id_token.verify_oauth2_token(credential, GoogleRequest(), client_id)
    except TransportError as error:
        raise HTTPException(503, '구글 인증 서버에 연결할 수 없습니다. 다시 시도해 주세요.') from error
    except (GoogleAuthError, ValueError, TypeError) as error:
        raise HTTPException(401, '유효하지 않거나 만료된 구글 로그인입니다.') from error
    if (claims.get('aud') != client_id
            or claims.get('iss') not in {'accounts.google.com', 'https://accounts.google.com'}
            or not isinstance(claims.get('sub'), str) or not claims['sub']
            or claims.get('email_verified') is not True
            or not isinstance(claims.get('email'), str)
            or not isinstance(claims.get('nonce'), str)):
        raise HTTPException(401, '구글 계정 정보를 확인할 수 없습니다.')
    return claims
