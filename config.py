from environs import Env

from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    user: str
    password: str
    database: str
    host: str
    port: int = 5432

@dataclass
class Config:
    db: DatabaseConfig
    api_host: str

def load_config() -> Config:
    env = Env()
    env.read_env() 

    return Config(
        db=DatabaseConfig(
            user=env.str("DB_USER"),
            password=env.str("DB_PASS"),
            database=env.str("DB_NAME"),
            host=env.str("DB_HOST"),
            port=env.int("DB_PORT", 5432)
        ),
        api_host=env.str("API_HOST", "0.0.0.0")
    )