from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from shared_models.enums import SemVerConstraint

from pydantic import BaseModel
from neo4j.graph import Node, Relationship


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Enums ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
class CiCdUsed(str, Enum):
    GITHUB_ACTIONS = "github-actions"
    JENKINS = "jenkins"  # Not always possible to detect this bc cicd could be conf'd server side
    TRAVIS = "travis"
    CIRCLE = "circle"
    NOT_USED = "not-used"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Nodes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
class Package(BaseModel):
    name: str
    language: str
    description: Optional[str]
    license: str
    homepage_url: Optional[str]
    repo_url: str
    author: Optional[str]
    maintainer: Optional[List[str]]
    indexed_at: datetime

    def graph_prop_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.lower(),
            "language": self.language,
            "description": self.description,
            "license": self.license,
            "homepage_url": self.homepage_url,
            "repo_url": self.repo_url,
            "author": self.author,
            "maintainer": self.maintainer,
        }

    @classmethod
    def from_node(cls, package_node: Node):
        # Validate Node Type
        if "Package" not in package_node.labels:
            raise LookupError("Input node is not of type Package")
        return cls(
            name=package_node["name"].lower(),
            language=package_node["language"],
            description=package_node["description"],
            license=package_node["license"],
            homepage_url=package_node["homepage_url"],
            repo_url=package_node["repo_url"],
            author=package_node["author"],
            maintainer=package_node["maintainer"],
            indexed_at=datetime.fromtimestamp(int(package_node["indexed_at"]/1000))
        )


class PackageVersion(BaseModel):
    version: str
    change_notes: Optional[str] = None
    vcs_tag: Optional[str] = None  # the SHA for the GitTag object of the tag
    indexed_at: Optional[datetime] = None

    def graph_prop_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "change_notes": self.change_notes,
            "vcs_tag": self.vcs_tag
        }

    @classmethod
    def from_node(cls, version_node: Node):
        # Validate Node Type
        if "PackageVersion" not in version_node.labels:
            raise LookupError("Input node is not of type PackageVersion")
        return cls(
            version=version_node["version"],
            change_notes=version_node["change_notes"],
            vcs_tag=version_node["vcs_tag"],
            indexed_at=datetime.fromtimestamp(int(version_node["indexed_at"]/1000)),
        )


class GitSnapshot(BaseModel):
    stars: int
    forks: int
    watchers: int
    issue_count: int
    contributor_count: int
    active_contributor_count: int
    ci_cd: CiCdUsed
    indexed_at: Optional[datetime] = None

    def graph_prop_dict(self) -> Dict[str, Any]:
        return {
            "stars": self.stars,
            "forks": self.forks,
            "watchers": self.watchers,
            "issues": self.issue_count,
            "contributors": self.contributor_count,
            "active_contributors": self.active_contributor_count,
            "ci_cd": self.ci_cd
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Edges ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
class DependencyEdge(BaseModel):  # source<PackageVersion> --DependsOn-> target<Package>
    source_package: Package
    source_version: PackageVersion
    target: Package
    version: str
    constraint: SemVerConstraint

    def graph_prop_dict(self) -> Dict[str, Any]:
        ...


class ResolvedDependencyEdge(BaseModel):  # source<PackageVersion> --HasResolvedDependencyOn-> target<PackageVersion>
    source: PackageVersion
    target: PackageVersion

    def graph_prop_dict(self) -> Dict[str, Any]:
        ...


class ReleaseEdge(BaseModel):  # package<Package> --Released-> version<PackageVersion>
    package: Package
    version: PackageVersion
    released_at: datetime

    def graph_prop_dict(self) -> Dict[str, Any]:
        return {
            **self.package.graph_prop_dict(),
            **self.version.graph_prop_dict(),
            "released_at": self.released_at.timestamp()*1000
        }

    @classmethod
    def from_relation(cls, release_relation: Relationship):
        # Validate Relation Type
        if release_relation.type != "Released":
            raise LookupError("Input relation is not of type Released")

        return cls(
            package=Package.from_node(release_relation.nodes[0]),
            version=PackageVersion.from_node(release_relation.nodes[1]),
            released_at=datetime.fromtimestamp(int(release_relation["released_at"]/1000)),
        )


class CapturedEdge(BaseModel):  # snapshot<GitSnapshot> --Captured-> package<Package>
    snapshot: GitSnapshot
    package: Package
    captured_at: datetime

    def graph_prop_dict(self) -> Dict[str, Any]:
        return {
            **self.package.graph_prop_dict(),
            **self.snapshot.graph_prop_dict(),
            "captured_at": self.captured_at.timestamp()*1000
        }
