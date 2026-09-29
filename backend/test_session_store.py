import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import get_engine, init_db
from services.multi_stage_service import create_session, submit_stage_answer
from services.session_store import load_session, save_session


class SessionPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DATABASE_URL': f"sqlite:///{(Path(self.temp.name) / 'db.sqlite').as_posix()}"})
        self.env.start()
        get_engine.cache_clear()
        init_db()

    def tearDown(self):
        get_engine().dispose()
        get_engine.cache_clear()
        self.env.stop()
        self.temp.cleanup()

    def test_progress_and_retry_survive_new_engine(self):
        sid = create_session('voice-phishing', owner='guest:test')['session_id']
        with patch('services.multi_stage_service.analyze_answer_with_llm', return_value={'llm_available': False}):
            first = submit_stage_answer(sid, '전화를 끊는다', 'retry-1', 1)
        get_engine().dispose()
        get_engine.cache_clear()
        self.assertEqual(submit_stage_answer(sid, '전화를 끊는다', 'retry-1', 1), first)
        data, _ = load_session(sid)
        self.assertEqual(data['owner'], 'guest:test')
        self.assertEqual(len(data['stage_results']), 1)

    def test_stale_writer_cannot_overwrite_winner(self):
        sid = create_session('voice-phishing')['session_id']
        first, first_version = load_session(sid)
        second, second_version = load_session(sid)
        first['current_stage'] = 2
        second['current_stage'] = 3
        self.assertTrue(save_session(first, first_version))
        self.assertFalse(save_session(second, second_version))
        self.assertEqual(load_session(sid)[0]['current_stage'], 2)
