"""Reported final scores stay bounded without changing raw evaluation or endings."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from data.branches import ENDINGS
from services import multi_stage_service as svc
from services.simulator_service import analyze_answer


class ScoreBoundsTests(unittest.TestCase):
    def session(self, scenario, score):
        return {
            'session_id': 'test-session', 'scenario_id': scenario, 'current_stage': 1,
            'total_score': score, 'stage_results': [], 'action_history': [],
            'conversation_history': [], 'description': '상황', 'question': '질문',
            'messages': [], 'branch': None, 'ending_type': None, 'is_finished': False,
        }

    def test_every_scenario_ending_and_boundary(self):
        for scenario in ['voice-phishing', 'jeonse-fraud', 'investment-fraud']:
            for ending, (risk_level, _, _) in ENDINGS.items():
                for raw, expected in [(-300, 0), (-1, 0), (0, 0), (50, 50),
                                      (100, 100), (101, 100), (300, 100)]:
                    with self.subTest(scenario=scenario, ending=ending, raw=raw):
                        session = self.session(scenario, raw)
                        finished = svc._finish(session, ending)
                        self.assertEqual(finished['total_score'], expected)
                        with patch.object(svc, 'get_session', return_value=deepcopy(session)):
                            result = svc.get_session_result('test-session')
                        self.assertEqual(result['total_score'], expected)
                        self.assertEqual(result['score'], None if risk_level == 'unknown' else expected)
                        self.assertEqual(result['ending_type'], ending)
                        self.assertEqual(result['risk_level'], risk_level)
                        self.assertEqual(session['total_score'], raw)

    def test_progress_and_stage_raw_scores_are_not_clamped(self):
        session = self.session('voice-phishing', -45)
        session['stage_results'] = [{'stage': 1, 'score': -45}]
        self.assertEqual(svc._response(session)['total_score'], -45)
        svc._finish(session, 'risk_continues')
        with patch.object(svc, 'get_session', return_value=session):
            result = svc.get_session_result('test-session')
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['stage_results'][0]['score'], -45)

    def test_legacy_endpoint_score_is_bounded_and_risk_stays_high(self):
        result = analyze_answer('voice-phishing', '송금한다')
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['risk_level'], 'high')
        for scenario in ['voice-phishing', 'jeonse-fraud', 'investment-fraud']:
            for points, expected in [(-200, 0), (50, 50), (200, 100)]:
                rule = {'keywords': ['테스트'], 'score': points, 'action': '테스트', 'feedback': '테스트'}
                with patch('services.simulator_service.SCENARIO_RULES', {scenario: [rule]}):
                    self.assertEqual(analyze_answer(scenario, '테스트')['score'], expected)


if __name__ == '__main__':
    unittest.main()
