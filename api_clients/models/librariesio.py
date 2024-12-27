import datetime
from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, AwareDatetime

from shared_models.packages import PackageLanguage


class SortDirection(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class SortKey(str, Enum):
    RANK = "rank"  # SourceRank score
    STARS = "stars"  # GitHub Stars
    DEPENDENTS = "dependents_count"  # How many packages depend on it
    LATEST_RELEASE = "latest_release_published_at"
    CONTRIBUTIONS = "contributions_count"


class VersionEntry(BaseModel):
    number: str
    published_at: str


class SearchResult(BaseModel):
    # Basic Package Info
    name: str
    language: PackageLanguage
    versions: List[VersionEntry]
    description: Optional[str] = None
    licenses: Optional[Union[str, List[str]]] = None
    homepage: Optional[str] = None
    repository_url: Optional[str] = None

    # Metrics
    rank: Optional[int] = None
    contributions_count: Optional[int] = None
    dependent_repos_count: Optional[int] = None
    dependents_count: Optional[int] = None
    forks: Optional[int] = None
    stars: Optional[int] = None

    # Release Info
    latest_release_number: Optional[str] = None
    latest_release_published_at: Optional[AwareDatetime] = None
    latest_stable_release_number: Optional[str] = None
    latest_stable_release_published_at: Optional[AwareDatetime] = None

    def get_version_info(self, version: str) -> Optional[datetime.datetime]:
        for item in self.versions:
            if item.number == version:
                return datetime.datetime.strptime(item.published_at.split(".")[0],"%Y-%m-%dT%H:%M:%S")
        return None

    def __hash__(self) -> int:
        return self.__str__().__hash__()
