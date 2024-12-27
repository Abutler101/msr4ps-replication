import datetime
import math
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Dict

import github.GithubException
from github import Github, Auth
from github.GitRef import GitRef
from github.Repository import Repository
from git import Repo, GitCommandError
from loguru import logger

from api_clients.client_configs import GithubConf
from api_clients.models.github import VersionInfo
from shared_models.graph_models import GitSnapshot, CiCdUsed


class GithubClient:
    config: GithubConf
    auth: Auth.Token

    def __init__(self, config: GithubConf = GithubConf()):
        self.config = config
        self.auth = Auth.Token(self.config.auth_token)

    def vcs_tag_to_commit_hash(self, repo_url: str, vcs_tag: str) -> str:
        repo_identifier = self._repo_url_to_identifier(repo_url)
        git_api = Github(auth=self.auth, base_url=self.config.api_url)
        repo = git_api.get_repo(repo_identifier)
        tags = list(repo.get_tags())
        target_tag = repo.get_git_tag(vcs_tag)
        for tag in tags:
            if tag.name == target_tag.tag:
                return tag.commit.sha
        raise ValueError(f"Could not find tag {target_tag.tag} in {repo_url}")

    def get_git_repo(self, repo_identifier: str) -> Repository:
        """
        repo_identifier is expected to be in the form: owner/repository as seen in git urls:
        https://github.com/Microsoft/TypeScript.git --> microsoft/typescript
        """
        github = Github(auth=self.auth, base_url=self.config.api_url)
        repo = github.get_repo(repo_identifier)
        return repo

    def get_version_info(self, repo_url: str, version: str) -> VersionInfo:
        if repo_url == "~MISSING~":
            return VersionInfo(vcs_tag=None, change_notes=None)
        try:
            repo_identifier = self._repo_url_to_identifier(repo_url)
        except NotImplementedError as err:
            logger.info(f"{repo_url} isn't a github url so can't pull version info")
            return VersionInfo(vcs_tag=None, change_notes=None)

        git_api = Github(auth=self.auth, base_url=self.config.api_url)
        try:
            repo = git_api.get_repo(repo_identifier)
        except github.GithubException as err:
            logger.warning(f"Failed to get repo for {repo_url}, identifier: {repo_identifier}")
            return VersionInfo(vcs_tag=None, change_notes=None)


        logger.debug(f"Getting Releases and tagrefs")
        url = repo.clone_url
        temp_dir = tempfile.TemporaryDirectory()
        local_repo = Repo.clone_from(url, to_path=temp_dir.name, progress=self._log_clone_progress)
        local_git_executor = local_repo.git
        try:
            tag_ref_result = local_git_executor.execute(
                ["git", "show-ref", "--tags"]
            )
        except GitCommandError as err:
            logger.warning(f"Got exception while running show-ref --tags on {url}")
            tag_ref_result = ""

        temp_dir.cleanup()

        # Produce Dict {tag name: commit hash}
        tag_refs = tag_ref_result.splitlines()
        tags = {entry.split(" ")[1]: entry.split(" ")[0] for entry in tag_refs}

        vcs_tag: Optional[str] = None
        change_notes: Optional[str] = None
        releases = repo.get_releases()
        logger.debug(f"{releases.totalCount} releases found")

        if releases.totalCount > 0:  # Project uses releases, try to match a correct one
            target_release = None
            for release in releases:
                if self._is_tag_name_for_version(release.tag_name, version):
                    target_release = release
                    target_tag_ref = self._get_ref_by_tag_name(release.tag_name, tags)
                    if target_tag_ref is None:
                        continue
                    vcs_tag = target_tag_ref
                    logger.info(
                        f"Suspected VCS Release Found for {repo_identifier} {version}. "
                        f"release tag: {release.tag_name} tag sha: {vcs_tag}"
                    )
                    break
            if target_release is None:
                logger.info(f"Unable to find release for {repo_identifier} {version}")
            else:
                change_notes = target_release.body

        else:  # Repo isn't configured to do releases, just try to pull the vcs_tag
            logger.debug(f"Looking through list of {len(tags)} refs")
            for tag_name, commit_hash in tags.items():
                if self._is_tag_name_for_version(tag_name.replace("refs/tags/",""), version):
                    vcs_tag = commit_hash

        return VersionInfo(
            vcs_tag=vcs_tag,
            change_notes=change_notes
        )

    def capture_vcs_snapshot(self, repo_url: str) -> Optional[GitSnapshot]:
        try:
            repo_identifier = self._repo_url_to_identifier(repo_url)
        except NotImplementedError as err:
            logger.info(f"{repo_url} isn't a github url so can't get GitSnapshot")
            return None
        git_api = Github(auth=self.auth, base_url=self.config.api_url)
        try:
            repo = git_api.get_repo(repo_identifier)
        except github.GithubException as err:
            if err.status == 404:
                logger.info(f"{repo_url} no longer exists so can't get GitSnapshot")
                return None
            else:
                raise err

        try:
            issue_count = repo.get_issues(state="open").totalCount
        except github.GithubException as err:
            issue_count = -1

        try:
            contrib_count = repo.get_contributors().totalCount
        except github.GithubException as err:
            contrib_count = -1

        active_contrib_count = self._get_active_contrib_count(repo)

        return GitSnapshot(
            stars=repo.stargazers_count,
            forks=repo.forks,
            watchers=repo.watchers,
            issue_count=issue_count,
            contributor_count=contrib_count if contrib_count != -1 else active_contrib_count,
            active_contributor_count=active_contrib_count,
            ci_cd=self._check_for_ci_cd(repo),
        )

    def _repo_url_to_identifier(self, url: str) -> str:
        web_url = url.replace("git+", "").replace(".git", "")
        if "github.com/" not in web_url:
            raise NotImplementedError(
                f"Repo metadata building is only supported for repos on github, {url} is not a recognised github url"
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
                f"UN-SUPPORTED REPO URL, {url}"
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

    @staticmethod
    def _get_ref_by_tag_name(tag_name: str, tags: Dict[str, str]) -> Optional[str]:
        logger.debug(f"Looking for {tag_name} in dict of {len(tags)} refs")
        return tags.get(f"refs/tags/{tag_name}", None)

    @staticmethod
    def _is_tag_name_for_version(name: str, target_version: str) -> bool:
        """
        Checks tag name for the target version, rejects false positives where target_version
        forms part of some other version
        """
        if target_version is None or target_version == "":
            return False
        return name.endswith(target_version) and not name.split(target_version)[0].endswith(".")

    @staticmethod
    def _page_contains_tag_refs(page: List[GitRef]) -> bool:
        return any(["refs/tags/" in ref.ref for ref in page])

    def _get_active_contrib_count(self, repo: Repository):
        logger.debug("checking for active contribs")
        six_months_ago = datetime.datetime.now() - datetime.timedelta(weeks=24)

        clone_url = repo.clone_url
        temp_dir = tempfile.TemporaryDirectory()
        local_repo = Repo.clone_from(clone_url, to_path=temp_dir.name, progress=self._log_clone_progress)
        local_git_executor = local_repo.git
        active_contributors: Dict[str, int]

        logger.info(f"Running command for last 6 months of commits")
        try:
            commit_log_result = local_git_executor.execute(
                ["git", "log",
                 f"--since={six_months_ago}",
                 '--pretty="%H - %an - %ae"'
                 ]
            )
            last_six_months_commits = commit_log_result.split("\n")
            if len(last_six_months_commits) == 1 and last_six_months_commits[1] == "":
                return 0
        except Exception:
            logger.warning(f"Got exception trying to get last 6 months of commits")
            last_six_months_commits = []
            temp_dir.cleanup()

        contributors = dict()
        for commit in last_six_months_commits:
            if len(commit) < 2:
                continue
            commit_split = commit.split(" - ")
            hash = commit_split[0]
            name = commit_split[1] if len(commit_split) == 3 else commit_split[2]
            email = commit_split[-1]
            key = email or name  # Prefer email, but use name if email is None
            contributors[key] = contributors.get(key, 0) + 1

        active_contributors = {k: v for k, v in contributors.items() if v > 2}

        temp_dir.cleanup()
        return len(active_contributors)

    def _check_for_ci_cd(self, repo: Repository) -> CiCdUsed:
        url = repo.clone_url
        temp_dir = tempfile.TemporaryDirectory()

        ci_cd = CiCdUsed.NOT_USED
        Repo.clone_from(url, to_path=temp_dir.name, progress=self._log_clone_progress)
        if Path(temp_dir.name).joinpath(".github/workflows").exists():
            ci_cd = CiCdUsed.GITHUB_ACTIONS
        elif Path(temp_dir.name).joinpath("Jenkinsfile").exists():
            ci_cd = CiCdUsed.JENKINS
        elif Path(temp_dir.name).joinpath(".circleci").exists():
            ci_cd = CiCdUsed.CIRCLE
        elif Path(temp_dir.name).joinpath(".travis.yml").exists():
            ci_cd = CiCdUsed.TRAVIS

        temp_dir.cleanup()
        return ci_cd

    @staticmethod
    def _log_clone_progress(op_code: int, cur_count: float, max_count: Optional[float] = None, message=""):
        if max_count is not None:
            progress = (cur_count / max_count) * 100
            if int(progress) % 25 == 0:
                logger.debug(
                    f"Opcode: {op_code} - Current Count: {cur_count}, Max Count: {max_count}, "
                    f"{progress:.2f}% Complete - msg={message}"
                )

