import shutil
from pathlib import Path

import docker
from docker.errors import ContainerError
from git import Repo
from loguru import logger


def bandit_on_repo(repo_url: str) -> int:
    _get_repo(repo_url)
    logger.debug(f"Cloned {repo_url} into dir: target-repo")
    _build_docker_image()
    _run_bandit()

    vuln_count = ...
    return vuln_count


def _get_repo(repo_url: str):
    logger.debug(f"Cleaning repo clone path")
    repo_path = Path(__file__).parent.joinpath("target-repo")
    shutil.rmtree(repo_path, ignore_errors=True)
    logger.debug(f"Cloning {repo_url}...")
    target_repo = Repo.clone_from(repo_url, to_path=repo_path)


def _build_docker_image():
    image_path = Path(__file__).parent.joinpath("bandit-on-repo.Dockerfile")
    docker_client = docker.from_env()
    logger.debug(f"Building Docker image...")
    docker_client.images.build(
        path=image_path.parent.as_posix(), dockerfile=image_path.name, tag="alexis-butler/bandit-on-repo"
    )


def _run_bandit() -> str:
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
    print()
