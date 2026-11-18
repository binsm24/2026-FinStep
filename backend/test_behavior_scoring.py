from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from database import get_engine, init_db
from services import multi_stage_service as svc
from services.scoring import SCORING_VERSION, calculate_score
from services.session_store import load_session, save_session


def action(kind, status='planned', historical=False):
    return {'type': kind, 'status': status, 'historical': historical, 'evidence': '사용자 원문'}


class BehaviorScoringTests(unittest.TestCase):
    def test_rubric_examples(self):
        end = action('end_contact')
        official = action('official_verification')
        docs = action('check_documents')
        help_ = action('consult_others')
        hold = action('stop_or_delay')
        money = action('transfer_money')
        paid = action('transfer_money', 'completed', True)
        cases = [
            ([end], 'safe_exit', 90),
            ([end, official], 'safe_exit', 100),
            ([end, help_], 'safe_exit', 95),
            ([end, docs, help_], 'safe_exit', 95),
            ([end, official, help_], 'safe_exit', 100),
            ([hold], 'safe_hold', 75),
            ([hold, official], 'safe_hold', 85),
            ([hold, docs, help_], 'safe_hold', 85),
            ([hold, official, help_], 'safe_hold', 90),
            ([money, end], 'safe_exit', 55),
            ([money, end, official], 'safe_exit', 65),
            ([paid, end], 'recovery', 20),
            ([paid, end, official], 'recovery', 30),
            ([action('provide_personal_info', 'completed'), end], 'recovery', 35),
            ([action('sign_contract', 'completed'), end], 'recovery', 30),
            ([paid, action('provide_personal_info', 'completed'), end, official], 'recovery', 0),
            ([money, official], 'risk_continues', 25),
            ([hold, official, money], 'risk_continues', 39),
            ([money], 'risk_continues', 15),
            ([money, money, end], 'safe_exit', 55),
            ([action('invest_money'), money, end], 'safe_exit', 55),
            ([action('transfer_money', 'negated')], 'safe_hold', 75),
            ([official], 'safe_hold', 60),
            ([help_], 'safe_hold', 55),
            ([], 'insufficient_information', None),
            ([end], 'insufficient_information', None),
            ([action('end_contact', 'negated')], 'insufficient_information', None),
        ]
        for actions, ending, expected in cases:
            with self.subTest(actions=actions, ending=ending):
                report = calculate_score(actions, ending)
                self.assertEqual(report['score'], expected)
                self.assertEqual(report['score_breakdown']['final_score'], expected)
                self.assertEqual(report['scoring_version'], SCORING_VERSION)

    def test_risk_category_weights_and_completion_upgrade(self):
        for kind, planned, completed in [('transfer_money', 35, 70), ('invest_money', 35, 70),
                                         ('provide_personal_info', 25, 55), ('sign_contract', 30, 60),
                                         ('trust_and_follow', 15, 20)]:
            for status, penalty in [('planned', planned), ('completed', completed)]:
                with self.subTest(kind=kind, status=status):
                    report = calculate_score([action(kind, status), action('end_contact')], 'safe_exit')
                    self.assertEqual(report['score'], 90 - penalty)
            report = calculate_score([action(kind), action(kind, 'completed'), action('end_contact')], 'recovery')
            self.assertEqual(report['score_breakdown']['risk_penalty'], completed)

    def test_repetitions_stage_splits_wording_and_order_do_not_change_score(self):
        original = [action('transfer_money'), action('end_contact'), action('official_verification')]
        repeated = [{**item, 'stage': stage, 'evidence': f'다른 표현 {stage}'}
                    for stage in range(1, 5) for item in original]
        for items in [original, repeated, list(reversed(repeated))]:
            before = deepcopy(items)
            self.assertEqual(calculate_score(items, 'safe_exit')['score'], 65)
            self.assertEqual(items, before)

    def test_concrete_risk_suppresses_general_compliance_and_returns_evidence(self):
        report = calculate_score([action('trust_and_follow'), action('transfer_money'),
                                  action('end_contact')], 'safe_exit')
        breakdown = report['score_breakdown']
        self.assertEqual(report['score'], 55)
        self.assertEqual(breakdown['risk_penalty'], 35)
        self.assertEqual(len(breakdown['suppressed_risks']), 1)
        self.assertEqual(breakdown['risk_categories'][0]['action']['evidence'], '사용자 원문')

    def test_safety_surplus_cannot_cancel_risk(self):
        report = calculate_score([action('end_contact'), action('official_verification'),
                                  action('consult_others'), action('transfer_money')], 'safe_exit')
        self.assertEqual(report['score'], 65)
        self.assertEqual(report['score_breakdown']['protected_base'], 100)

    def test_historical_plans_and_safe_negations_are_not_positive_actions(self):
        items = [action('end_contact', 'negated'), action('transfer_money', historical=True),
                 action('official_verification', historical=True)]
        self.assertIsNone(calculate_score(items, 'safe_hold')['score'])
        self.assertIsNone(calculate_score(items, 'safe_hold')['score_breakdown']['base_score'])


class BehaviorSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DATABASE_URL': f"sqlite:///{(Path(self.temp.name) / 'test.db').as_posix()}"})
        self.env.start()
        get_engine.cache_clear()
        init_db()
        self.llm = patch.object(svc, 'analyze_answer_with_llm', return_value={'llm_available': False})
        self.llm.start()
        self.dialogue = patch.object(svc, 'generate_next_response', side_effect=lambda **kw: {'message': kw['next_stage_message']})
        self.dialogue.start()

    def tearDown(self):
        self.dialogue.stop()
        self.llm.stop()
        get_engine().dispose()
        get_engine.cache_clear()
        self.env.stop()
        self.temp.cleanup()

    def test_real_inputs_early_exit_and_retry_persist_score(self):
        for scenario in ['voice-phishing', 'jeonse-fraud', 'investment-fraud']:
            for answer, expected in [('전화를 끊는다', 90),
                                     ('전화를 끊는다. 공식 기관에 확인한다', 100)]:
                sid = svc.create_session(scenario)['session_id']
                response = svc.submit_stage_answer(sid, answer, 'same-request', 1)
                self.assertEqual(response['total_score'], expected)
                self.assertEqual(svc.submit_stage_answer(sid, answer, 'same-request', 1), response)
                get_engine().dispose()
                get_engine.cache_clear()
                report = svc.get_session_result(sid)
                stored, _ = load_session(sid)
                self.assertEqual(report['score'], expected)
                self.assertEqual(report['score_breakdown'], stored['score_breakdown'])
                self.assertEqual(report['scoring_version'], SCORING_VERSION)
                self.assertIsNone(report['stage_results'][0]['score'])

    def test_completed_exposure_then_exit_and_no_interim_score(self):
        sid = svc.create_session('voice-phishing')['session_id']
        result = svc.submit_stage_answer(sid, '이미 송금했다')
        self.assertIsNone(result['total_score'])
        result = svc.submit_stage_answer(sid, '전화를 끊는다')
        self.assertEqual(result['ending_type'], 'recovery')
        self.assertEqual(result['total_score'], 20)
        self.assertEqual(svc.get_session_result(sid)['score'], 20)

    def test_legacy_in_progress_session_keeps_original_rubric(self):
        sid = svc.create_session('voice-phishing')['session_id']
        session, version = load_session(sid)
        session.pop('scoring_version')
        session['total_score'] = 0
        save_session(session, version)
        svc.submit_stage_answer(sid, '전화를 끊는다')
        report = svc.get_session_result(sid)
        self.assertEqual(report['scoring_version'], 'legacy-v0')
        self.assertEqual(report['score'], 25)
        self.assertIsNone(report['score_breakdown'])

    def test_all_scenarios_hold_and_risky_endings(self):
        for scenario in ['voice-phishing', 'jeonse-fraud', 'investment-fraud']:
            for risky, expected in [(False, 85), (True, 39)]:
                sid = svc.create_session(scenario)['session_id']
                for stage in range(1, 5):
                    actions = [action('stop_or_delay'), action('official_verification')]
                    if risky and stage == 4:
                        actions = [action('transfer_money')]
                    with patch.object(svc, 'analyze_answer_with_llm', return_value={
                            'actions': actions, 'ambiguous': False, 'llm_available': True}):
                        response = svc.submit_stage_answer(sid, '대응 선택')
                    if stage < 4:
                        self.assertIsNone(response['total_score'])
                report = svc.get_session_result(sid)
                self.assertEqual(report['score'], expected)
                self.assertEqual(response['total_score'], expected)
                self.assertEqual(report['ending_type'], 'risk_continues' if risky else 'safe_hold')

    def test_unknown_ending_preserves_exposure_but_has_no_score(self):
        sid = svc.create_session('voice-phishing')['session_id']
        with patch.object(svc, 'analyze_answer_with_llm', return_value={
                'actions': [action('transfer_money', 'completed', True)],
                'ambiguous': True, 'llm_available': True}):
            for _ in range(3):
                response = svc.submit_stage_answer(sid, '현재 행동은 불명확')
        report = svc.get_session_result(sid)
        self.assertEqual(report['ending_type'], 'insufficient_information')
        self.assertIsNone(report['score'])
        self.assertIsNone(response['total_score'])
        self.assertEqual(report['score_breakdown']['risk_penalty'], 70)
        self.assertTrue(report['risky_actions'])


if __name__ == '__main__':
    unittest.main()
