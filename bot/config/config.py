from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    USE_REF: bool = True
    REF_ID: str = 'xDZm2M3t'

    USE_RANDOM_DELAY_IN_RUN: bool = True
    RANDOM_DELAY_IN_RUN: list[int] = [5, 80]
    RANDOM_DELAY_IN_RUN_STATISTICS: list[int] = [5, 20]

    SLEEP_TIME_IN_MINUTES: list[int] = [60 * 24, 60 * 24]

    ENABLE_AUTO_TASKS: bool = True
    UNSAFE_ENABLE_JOIN_TG_CHANNELS: bool = False # NOT RECOMMENDED
    MUTE_AND_ARCHIVE_TG_CHANNELS: bool = False

    DISABLE_IN_NIGHT: bool = False
    NIGHT_TIME: list[int] = [23, 6]

    TASKS_BLACK_LIST: list[str] = []
    TASKS_TODO_LIST: list[str] = []

    USE_PROXY_FROM_FILE: bool = True

    MAX_RETRIES: int = 3

    ENABLE_SSL: bool = False
    ENABLE_CLOUDS_SCRAPER: bool = True

    ENABLE_CHECKER: bool = False # DONT TOUCH THIS

settings = Settings()


