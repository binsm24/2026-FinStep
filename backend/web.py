"""Serve the production SPA and API from the same origin."""
import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_frontend(app):
    configured = os.getenv('FRONTEND_DIST')
    if not configured:
        return
    folder = Path(configured).resolve()
    if not (folder / 'index.html').is_file():
        raise RuntimeError('FRONTEND_DIST must contain the built frontend index.html')

    # Replace the development API greeting with the frontend home page.
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, 'path', None) != '/']
    app.mount('/assets', StaticFiles(directory=folder / 'assets'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path.split('/')[0] in {'api', 'health', 'docs', 'redoc', 'openapi.json'}:
            raise HTTPException(404)
        target = (folder / path).resolve()
        if not target.is_relative_to(folder):
            raise HTTPException(404)
        if target.is_file():
            return FileResponse(target)
        if Path(path).suffix:
            raise HTTPException(404)
        return FileResponse(folder / 'index.html', headers={'Cache-Control': 'no-cache'})
