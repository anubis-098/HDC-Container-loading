import logging
import time
from app.core.config import settings
from app.workers.archive import run

if __name__ == '__main__':
    while True:
        try:
            if settings().archive_enabled:
                while run():
                    pass
            time.sleep(86400)
        except Exception:
            logging.exception('Archive failed; keeping source data until verified')
            time.sleep(3600)
