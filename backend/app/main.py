import logging
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from app.api.router import router
from app.api.downloads import router as downloads_router

app = FastAPI(title='CJ Logistics · Container Loading', version='0.2.0')
app.include_router(router, prefix='/api')
app.include_router(downloads_router, prefix='/api')

@app.middleware('http')
async def same_origin(request: Request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin = request.headers.get('origin')
        if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and urlsplit(origin).netloc != request.headers.get('host')):
            return JSONResponse({'detail':'ไม่อนุญาตคำขอจากเว็บไซต์อื่น'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(OperationalError)
async def database_error(request, error):
    logging.exception('Database unavailable', exc_info=error)
    return JSONResponse({'detail':'ฐานข้อมูลยังไม่พร้อม กรุณาลองใหม่'}, status_code=503)
