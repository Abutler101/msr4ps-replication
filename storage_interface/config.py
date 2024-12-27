from pathlib import Path

from pydantic_settings import BaseSettings


class Neo4jConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 7687
    password: str

    class Config:
        env_prefix = "neo4j_"
        env_file = Path(__file__).parents[1].joinpath(".env")
        extra = "ignore"
