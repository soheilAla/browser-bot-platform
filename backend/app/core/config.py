from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    selenium_remote_url: str = "http://localhost:4444"

    arcaptcha_target_url: str
    arcaptcha_username: str
    arcaptcha_password: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()  # type: ignore
