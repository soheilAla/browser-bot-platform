from pydantic_settings import BaseSettings, SettingsConfigDict


class ArcaptchaBotSettings(BaseSettings):
    email: str
    password: str
    target_url: str
    model_config = SettingsConfigDict(
        env_prefix="ARCAPTCHA_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


bot_settings = ArcaptchaBotSettings()  # type: ignore
