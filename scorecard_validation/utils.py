import re
import shutil
from pathlib import Path

from git import Repo
from loguru import logger

REPO_PATH = Path(__file__).parent.joinpath("target-repo")


def clone_repo(repo_id: str):
    logger.debug(f"Cleaning repo clone path")
    shutil.rmtree(REPO_PATH, ignore_errors=True)
    clone_url = f"git@github.com:{repo_id}.git"
    logger.debug(f"Cloning {repo_id} using {clone_url}...")
    target_repo = Repo.clone_from(clone_url, to_path=REPO_PATH)


def extract_repo_id(repo_url: str) -> str:
    """
    Extracts owner/repo from full repo url
    """
    web_url = repo_url.replace("git+", "").replace(".git", "")
    if "github.com/" not in web_url:
        raise NotImplementedError(
            f"Repo metadata building is only supported for repos on github, {repo_url} is not a recognised github url"
        )
    if "https://github.com/" in web_url:
        repo_path = web_url.replace("https://github.com/", "").lower()
    elif "http://github.com/" in web_url:
        repo_path = web_url.replace("http://github.com/", "").lower()
    elif "ssh://git@github.com/" in web_url:
        repo_path = web_url.replace("ssh://git@github.com/", "").lower()
    elif "git://github.com" in web_url:
        repo_path = web_url.replace("git://github.com", "").lower()
    elif re.match(r"https:\/\/.+@github.com\/", web_url):
        # Handles case of git+https://<USER>@github.com/XXX/YYY
        repo_path = re.sub("https://.+@github.com/", "", web_url).lower()
    elif web_url.startswith("github.com"):
        repo_path = web_url.replace("github.com", "").lower()
    elif web_url.startswith("git@github.com"):
        repo_path = web_url.replace("git@github.com", "").lower()
    else:
        raise ValueError(
            f"UN-SUPPORTED REPO URL, {repo_url}"
        )
    repo_path = repo_path.rstrip("/")
    slash_split = repo_path.split("/")
    drop_list = [
        "issues", "pulls", "releases", "actions", "discussions", "blob", "tarball", "tree", "archive", "tags",
    ]
    if len(slash_split) > 2 and (
            any(substring in slash_split[2] for substring in drop_list) or
            any(substring in slash_split[-1] for substring in drop_list)
    ):
        repo_path = "/".join(slash_split[:2])
    logger.debug(f"Git repo Path isolated as: {repo_path}")
    return repo_path
