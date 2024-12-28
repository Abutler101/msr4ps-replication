from pathlib import Path
from typing import Optional, List
import json

import docker
from docker.errors import ContainerError
from loguru import logger
from pydantic import BaseModel

from scorecard_validation.utils import clone_repo

IMAGE_PATH = Path(__file__).parent.joinpath("bandit-on-repo.Dockerfile")


class BanditIssue(BaseModel):
    code: str
    col_offset: int
    end_col_offset: int
    filename: str
    issue_confidence: str
    issue_cwe: dict
    issue_severity: str
    issue_text: str
    line_number: int
    line_range: list
    more_info: str
    test_id: str
    test_name: str


def bandit_on_repo() -> int:
    _build_docker_image()
    bandit_logs = _run_bandit()
    if bandit_logs is None:
        raise ValueError(f"Bandit Run Failed - No logs returned")
    detected_issues = _parse_bandit_logs(bandit_logs)
    vuln_count = _count_vulns(detected_issues)
    return vuln_count


def _build_docker_image():
    docker_client = docker.from_env()
    logger.debug(f"Building Docker image...")
    docker_client.images.build(
        path=IMAGE_PATH.parent.as_posix(), dockerfile=IMAGE_PATH.name, tag="alexis-butler/bandit-on-repo"
    )


def _run_bandit() -> Optional[str]:
    logger.debug(f"Running Bandit...")
    docker_client = docker.from_env()

    try:
        direct_out = docker_client.containers.run(
            image="alexis-butler/bandit-on-repo",
            stderr=True,
            stdout=True,
            command="-r target-repo -f json"
        )
    except ContainerError as err:
        bandit_logs = err.container.logs().decode("utf-8")
        err.container.remove()
        return bandit_logs
    return None


def _parse_bandit_logs(log_string: str) -> List[BanditIssue]:
    split_on_newlines = log_string.splitlines()
    index_of_json_start = split_on_newlines.index("{")
    if split_on_newlines[-1] != "}":
        raise ValueError("Can't Parse Bandit Logs")
    json_output = "\n".join(split_on_newlines[index_of_json_start:])
    parsed_json_out = json.loads(json_output)
    return [BanditIssue.model_validate(issue) for issue in parsed_json_out["results"]]


def _count_vulns(issues: List[BanditIssue]) -> int:
    vuln_count: int = 0
    for issue in issues:
        # Filter out certain top level dirs - everything will be under: target-repo/ so top level dirs are at split 1
        if "docs" in issue.filename.split("/")[1]:
            # Ignore any python code in a top level docs directory - likely examples etc.
            continue
        elif "tests" in issue.filename.split("/")[1]:
            # Ignore any python code in a top level tests directory - likely unit tests etc.
            continue
        elif issue.issue_severity == "LOW":
            # Ignore any Low severity issues - not really vulns
            continue
        vuln_count += 1
    return vuln_count
