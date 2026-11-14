from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_database_url: str = ''
    image_database_url: str = ''
    app_db_password: str = ''
    image_db_password: str = ''
    cookie_secure: bool = False
    photo_retention_days: int = Field(default=30, ge=1, le=3650)
    archive_directory: str = '/archives'
    archive_enabled: bool = False

@lru_cache
def settings():
    return Settings()
