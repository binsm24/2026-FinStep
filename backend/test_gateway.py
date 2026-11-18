import json
import unittest
from unittest.mock import patch

import httpx
from services import llm_service as llm


class GatewayTests(unittest.TestCase):
    def setUp(self):
        for name, value in [('provider', 'gateway'), ('gateway_api_key', 'test-key'),
                            ('gateway_model', 'gemini-3.8-flash'),
                            ('gateway_base_url', 'https://factchat-cloud.mindlogic.ai/v1/gateway')]:
            mock = patch.object(llm, name, value)
            mock.start()
            self.addCleanup(mock.stop)

    def response(self, content, finish='stop', refusal=None):
        return httpx.Response(200, request=httpx.Request('POST', llm.gateway_endpoint()),
                              json={'choices': [{'finish_reason': finish, 'message': {
                                  'content': content, 'refusal': refusal}}]})

    def analyze(self):
        return llm.analyze_answer_with_llm('보이스피싱', '1단계', '기관 사칭', '전화를 끊는다')

    def test_schema_auth_and_grounded_analysis(self):
        content = json.dumps({'actions': [{'type': 'end_contact', 'evidence': '전화를 끊는다',
                                          'status': 'planned', 'historical': False}], 'ambiguous': False})
        with patch.object(llm.httpx, 'post', return_value=self.response(content)) as post:
            result = self.analyze()
        self.assertTrue(result['llm_available'])
        self.assertEqual(result['actions'][0]['type'], 'end_contact')
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')
        self.assertEqual(kwargs['json']['model'], 'gemini-3.8-flash')
        self.assertEqual(kwargs['json']['reasoning_effort'], 'low')
        schema = kwargs['json']['response_format']['json_schema']
        self.assertTrue(schema['strict'])
        self.assertFalse(schema['schema']['additionalProperties'])
        self.assertFalse(kwargs['follow_redirects'])

    def test_invalid_refused_truncated_and_ungrounded_responses_fall_back(self):
        responses = [self.response('{}'), self.response('not json'), self.response('{}', 'length'),
                     self.response('{}', refusal='refused'),
                     self.response(json.dumps({'actions': [{'type': 'end_contact', 'evidence': '없는 원문',
                         'status': 'planned', 'historical': False}], 'ambiguous': False})),
                     httpx.Response(401, request=httpx.Request('POST', llm.gateway_endpoint()))]
        for response in responses:
            with self.subTest(response=response), patch.object(llm.httpx, 'post', return_value=response):
                self.assertFalse(self.analyze()['llm_available'])

    def test_timeout_and_missing_key_fall_back(self):
        with patch.object(llm.httpx, 'post', side_effect=httpx.ReadTimeout('timeout')):
            self.assertFalse(self.analyze()['llm_available'])
        with patch.object(llm, 'gateway_api_key', ''), patch.object(llm.httpx, 'post') as post:
            self.assertFalse(self.analyze()['llm_available'])
            post.assert_not_called()

    def test_contextual_dialogue_and_invalid_claim_fallback(self):
        for content, accepted in [
            ('{"message":"오늘 결정하기 어려우시면 언제쯤 가능하세요?"}', True),
            ('{"message":"송금이 완료됐습니다"}', False),
            ('{"choice":1}', False),
            ('{"message":""}', False),
        ]:
            with patch.object(llm.httpx, 'post', return_value=self.response(content)):
                result = llm.generate_next_response('제목', '현재', '대사', '오늘은 어려워요', '다음', '상황', '확인하세요.')
            self.assertEqual(result['llm_available'], accepted)
            self.assertEqual(result['message'], '오늘 결정하기 어려우시면 언제쯤 가능하세요?' if accepted else '확인하세요.')

    def test_reject_unsafe_base_url(self):
        for url in ['http://example.com', 'https://key@example.com', 'https://example.com?key=x']:
            with patch.object(llm, 'gateway_base_url', url), patch.object(llm.httpx, 'post') as post:
                self.assertFalse(self.analyze()['llm_available'])
                post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
