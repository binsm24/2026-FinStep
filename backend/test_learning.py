import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from data.learning import LEARNING_CONTENTS
from routers.learning import router


class LearningTests(unittest.TestCase):
    def test_six_concepts_have_five_valid_distinct_quizzes(self):
        self.assertEqual(len(LEARNING_CONTENTS), 6)
        all_ids = set()
        questions = set()
        for content in LEARNING_CONTENTS:
            self.assertNotIn('quiz', content)
            self.assertEqual(len(content['quizzes']), 5)
            for quiz in content['quizzes']:
                with self.subTest(quiz=quiz['id']):
                    self.assertNotIn(quiz['id'], all_ids)
                    self.assertNotIn(quiz['question'], questions)
                    all_ids.add(quiz['id'])
                    questions.add(quiz['question'])
                    self.assertEqual(len(quiz['options']), 4)
                    self.assertEqual(len(set(quiz['options'])), 4)
                    self.assertTrue(all(option.strip() for option in quiz['options']))
                    self.assertIs(type(quiz['answer_index']), int)
                    self.assertIn(quiz['answer_index'], range(4))
                    self.assertTrue(quiz['question'].strip())
                    self.assertTrue(quiz['explanation'].strip())
        self.assertEqual(len(all_ids), 30)

    def test_api_list_and_detail_expose_same_question_bank(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.get('/api/learning')
        self.assertEqual(response.status_code, 200)
        for content in response.json():
            detail = client.get(f"/api/learning/{content['id']}")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(content['quizzes'], detail.json()['quizzes'])
        self.assertEqual(client.get('/api/learning/missing').status_code, 404)


if __name__ == '__main__':
    unittest.main()
