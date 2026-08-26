from functools import lru_cache
from sqlalchemy.engine import URL
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    app_host: str
    app_port: int

    access_control_allow_origins: str

    remote_db_driver: str
    remote_db_host: str
    remote_db_port: int
    remote_db_user: str
    remote_db_password: str
    remote_db_name: str

    local_db_driver: str
    local_db_host: str
    local_db_port: int
    local_db_user: str
    local_db_password: str
    local_db_name: str

    mmdpawn_encrypt_pw: str
    mmdpawn_api_url: str

    trust_proxy: bool
    python_env: str
    log_level: str

    @field_validator('python_env', 'log_level', mode='after')
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower()

    @computed_field
    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.access_control_allow_origins.split(',') if o.strip()]

    @computed_field
    @property
    def remote_db_url(self) -> URL:
        return URL.create(
            drivername=self.remote_db_driver,
            username=self.remote_db_user,
            password=self.remote_db_password,
            host=self.remote_db_host,
            port=self.remote_db_port,
            database=self.remote_db_name,
        )


    @computed_field
    @property
    def local_db_url(self) -> URL:
        return URL.create(
            drivername=self.local_db_driver,
            username=self.local_db_user,
            password=self.local_db_password,
            host=self.local_db_host,
            port=self.local_db_port,
            database=self.local_db_name,
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()

