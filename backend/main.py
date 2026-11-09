import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from . import db


def create_app(engine=None, data_dir=None):
    engine = engine or db.make_engine()

    @asynccontextmanager
    async def lifespan(app):
        yield

    app = FastAPI(title='ImuniGuia', version='1.0.0', lifespan=lifespan)
    app.state.engine = engine
    app.state.data = Path(data_dir or os.environ.get('IMUNIGUI_DATA_DIR', 'data')).resolve()
    app.state.data.mkdir(parents=True, exist_ok=True)
    (app.state.data / 'uploads').mkdir(exist_ok=True)
    app.state.secure = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
    origin = os.environ.get('PUBLIC_ORIGIN', 'http://localhost:4173').rstrip('/')
    origins = {origin} | (set() if app.state.secure else {'http://localhost:3000', 'http://127.0.0.1:3000', 'http://127.0.0.1:4173'})

    @app.middleware('http')
    async def protect(request, call_next):
        if request.url.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if (request.headers.get('origin') and request.headers['origin'] not in origins) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'error': 'Origem não permitida.'}, status_code=403)
            length = request.headers.get('content-length')
            if length and (not length.isdecimal() or int(length) > 10 * 1024 * 1024 + 262144):
                return JSONResponse({'error': 'Requisição excede o limite.'}, status_code=413)
        response = await call_next(request)
        response.headers.update({'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'SAMEORIGIN', 'Permissions-Policy': 'camera=(self), microphone=(), geolocation=()'})
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data:; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'")
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(HTTPException)
    async def api_error(request, exc):
        return JSONResponse({'error': exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({'error': 'Confira os campos informados.', 'fields': ['.'.join(map(str, e['loc'][1:])) for e in exc.errors()]}, status_code=422)

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({'error': 'Este registro já existe ou foi alterado. Atualize a página.'}, status_code=409)

    @app.get('/api/health')
    def health():
        with engine.connect() as con:
            con.exec_driver_sql('SELECT 1')
        return {'ok': True, 'service': 'ImuniGuia upload-and-review'}

    from .routes import router
    app.include_router(router)
    dist = Path(__file__).resolve().parent.parent / 'dist'
    if (dist / 'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

    @app.get('/favicon.svg', include_in_schema=False)
    def favicon():
        return FileResponse(Path(__file__).resolve().parent.parent / 'public' / 'favicon.svg')

    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path.startswith('api/'):
            raise HTTPException(404, 'Rota não encontrada.')
        if not (dist / 'index.html').is_file():
            raise HTTPException(503, 'Execute npm run build para preparar a interface.')
        return FileResponse(dist / 'index.html')

    return app


app = create_app()
