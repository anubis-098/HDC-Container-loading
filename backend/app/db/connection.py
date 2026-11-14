from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from app.core.config import settings

@contextmanager
def connect(images=False):
    cfg = settings()
    url = cfg.image_database_url if images else cfg.app_database_url
    if url:
        connection = psycopg.connect(url.replace('postgresql+psycopg://', 'postgresql://'), row_factory=dict_row, connect_timeout=10)
    else:
        connection = psycopg.connect(host='postgres-images' if images else 'postgres-app', dbname='loading_images' if images else 'loading_app', user='images' if images else 'loading', password=cfg.image_db_password if images else cfg.app_db_password, row_factory=dict_row, connect_timeout=10)
    with connection as conn:
        yield conn
