import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from settings import allowed_origins
from web import mount_frontend


class DeploymentTests(unittest.TestCase):
    def test_render_origin_is_trusted_without_trusting_arbitrary_hosts(self):
        with patch.dict(os.environ, {'FRONTEND_ORIGINS': '', 'RENDER_EXTERNAL_URL': 'https://finstep.onrender.com/'}):
            self.assertEqual(allowed_origins(), ['https://finstep.onrender.com'])

    def test_spa_refresh_assets_api_and_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'dist'
            (folder / 'assets').mkdir(parents=True)
            (folder / 'index.html').write_text('<html>FinStep</html>')
            (folder / 'assets' / 'app.js').write_text('console.log(1)')
            (Path(temporary) / 'secret.txt').write_text('private')
            app = FastAPI()

            @app.get('/api/example')
            def example():
                return {'ok': True}

            with patch.dict(os.environ, {'FRONTEND_DIST': str(folder)}):
                mount_frontend(app)
            client = TestClient(app)
            for path in ['/', '/archive', '/learning/example']:
                self.assertEqual(client.get(path).text, '<html>FinStep</html>')
            self.assertEqual(client.get('/assets/app.js').status_code, 200)
            self.assertEqual(client.get('/api/example').json(), {'ok': True})
            for path in ['/api/missing', '/health/missing', '/missing.js', '/assets/missing.js', '/%2e%2e%2fsecret.txt']:
                self.assertEqual(client.get(path).status_code, 404, path)

    def test_missing_build_fails_at_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'FRONTEND_DIST': folder}):
                with self.assertRaises(RuntimeError):
                    mount_frontend(FastAPI())
