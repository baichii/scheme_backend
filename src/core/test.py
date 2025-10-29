from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    db_user: str
    db_password: str


settings = Settings()
print(settings.db_user)
