from pathlib import Path

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings


class GithubConf(BaseSettings):
    api_url: str = Field(default="http://0.0.0.0:9090/github_local")
    auth_token: str = Field(default="")

    class Config:
        env_prefix = "github_"
        env_file = Path(__file__).parents[1].joinpath(".env")
        extra = "ignore"
