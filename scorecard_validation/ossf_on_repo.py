import docker
from loguru import logger

from analysis.disc_ossf_scoring import GithubConf, OssfReport
from scorecard_validation.utils import extract_repo_id


def _eval_ossf(repo: str) -> float:
    """
    repo in format: owner/repo
    returns ossf score
    """
    docker_client = docker.from_env()
    logger.debug(f"Running Ossf Scorecard Docker Container against {repo}")
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


def ossf_on_repo(repo_id: str) -> float:
    return _eval_ossf(repo_id)
