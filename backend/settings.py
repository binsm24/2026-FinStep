import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / '.env')


def allowed_origins():
    origins = [origin.strip().rstrip('/') for origin in os.getenv(
        'FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173'
    ).split(',') if origin.strip()]
    external_url = os.getenv('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
    if external_url and external_url not in origins:
        origins.append(external_url)
    for key in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL'):
        host = os.getenv(key, '').strip()
        if host:
            origins.append('https://' + host)
    return origins


def secure_cookies():
    return os.getenv('COOKIE_SECURE', 'false').lower() == 'true'


def google_client_id():
    return os.getenv('GOOGLE_CLIENT_ID', '').strip()
