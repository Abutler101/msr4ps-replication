from pathlib import Path
from typing import List

import docker
import pandas as pd
from neo4j import Query
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings
from loguru import logger

from api_clients import GithubClient
from storage_interface.graph.neo4j_client import Neo4jClient

OUTPUT_DIR = Path(__file__).parent.joinpath("output")

package_git_url_query = Query(
    "MATCH (p:Package {name: $name})\n"
    "RETURN p.repo_url"
)


class GithubConf(BaseSettings):
    auth_token: str = Field(default="")

    class Config:
        env_prefix = "github_"
        env_file = Path(__file__).parent.joinpath(".env")
        extra = "ignore"


class OssfReport(BaseModel):
    date: str
    repo: dict
    scorecard: dict
    score: float
    checks: List[dict]


def eval_ossf(repo: str) -> float:
    """
    repo in format: owner/repo
    returns ossf score
    """
    docker_client = docker.from_env()
    raw_output = docker_client.containers.run(
        image="gcr.io/openssf/scorecard:stable",
        command=f"--repo={repo} --format=json",
        environment={"GITHUB_AUTH_TOKEN": GithubConf().auth_token},
        auto_remove=True
    )
    # Pull aggregate score out of raw_output and return
    ossf_report = OssfReport.model_validate_json(raw_output)
    aggregate_score = ossf_report.score
    return aggregate_score


def sec_vs_crit(target: str) -> pd.DataFrame:
    neo_client = Neo4jClient()
    # Read sampled packages csv
    sampled_packages_df = pd.read_csv(OUTPUT_DIR.joinpath(f"{target}/sampled_disc_packs.csv"), index_col=0)
    # For each row pull git link from graph db and call eval_ossf
    ossf_scores = []
    seen_packages = []
    for idx, row in sampled_packages_df.iterrows():
        if row.package_name.lower() in seen_packages:
            continue
        seen_packages.append(row.package_name.lower())

        try:
            raw_url_response = neo_client._run_query(
                package_git_url_query, {"name": row.package_name.lower()}, database=target
            ).values
            full_url = raw_url_response[0][0]
        except Exception as err:
            continue

        try:
            repo_identifier = GithubClient()._repo_url_to_identifier(full_url)
        except ValueError as err:
            continue
        except NotImplementedError as err:
            logger.warning(f"{row.package_name.lower()} missing repo link")
            continue

        try:
            logger.info(f"Scoring {repo_identifier} ({idx}/{len(sampled_packages_df)})...")
            score = eval_ossf(repo_identifier)
            logger.info(f"{repo_identifier} scored: {score}")
        except Exception as err:
            print(f"OSSF on {row.package_name} - {repo_identifier} failed")
            continue

        ossf_scores.append((row.package_name.lower(), score))

    # Put scores into df and return
    ossf_scores_df = pd.DataFrame(ossf_scores, columns=["package_name", "ossf_score"]).set_index("package_name")
    joined_result = sampled_packages_df.join(ossf_scores_df, "package_name", how="outer").dropna(subset=["ossf_score"])
    return joined_result


def main():
    npm_svc_df = sec_vs_crit("npm")
    npm_svc_df.to_csv(OUTPUT_DIR.joinpath("npm/disc-ossf-scores.csv"))
    logger.info(f"!!---------- NPM OSSF scoring complete ----------!!")
    # Average scores for each bin
    npm_bin_avgs:pd.DataFrame = npm_svc_df.groupby("bin").mean(numeric_only=True)
    # Save average scores to csv
    npm_bin_avgs.to_csv(OUTPUT_DIR.joinpath("npm/disc_bin_avgs.csv"))

    pypi_svc_df = sec_vs_crit("pypi")
    pypi_svc_df.to_csv(OUTPUT_DIR.joinpath("pypi/disc-ossf-scores.csv"))
    logger.info(f"!!---------- PyPi OSSF scoring complete ----------!!")
    # Average scores for each bin
    pypi_bin_avgs:pd.DataFrame = pypi_svc_df.groupby("bin").mean(numeric_only=True)
    # Save average scores to csv
    pypi_bin_avgs.to_csv(OUTPUT_DIR.joinpath("pypi/disc_bin_avgs.csv"))


if __name__ == '__main__':
    main()
