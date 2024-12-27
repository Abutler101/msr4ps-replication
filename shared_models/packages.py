from enum import Enum
from typing import Dict, List, Optional

from shared_models.enums import SemVerConstraint

from pydantic import BaseModel


class PackageLocation(str, Enum):
    NPM = "NPM"
    PYPI = "Pypi"
    CRATES_IO = "Cargo"


class PackageLanguage(str, Enum):
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    PYTHON = "Python"
    RUST = "Rust"
    OTHER = "OTHER"

    @classmethod
    def _missing_(cls, value):
        return cls.OTHER


LOCATION_TO_LANG_MAP: Dict[PackageLocation, List[PackageLanguage]] = {
    PackageLocation.NPM: [PackageLanguage.JAVASCRIPT, PackageLanguage.TYPESCRIPT],
    PackageLocation.PYPI: [PackageLanguage.PYTHON]
}


LANG_TO_LOCATION_MAP: Dict[PackageLanguage, PackageLocation] = {
    PackageLanguage.JAVASCRIPT: PackageLocation.NPM,
    PackageLanguage.TYPESCRIPT: PackageLocation.NPM,
    PackageLanguage.PYTHON: PackageLocation.PYPI
}


class PackageIdentifier(BaseModel):
    name: str
    location: PackageLocation


class PackageVersionIdentifier(PackageIdentifier):
    version: str

    def to_package_identifier(self) -> PackageIdentifier:
        return PackageIdentifier(
            name=self.name.lower(),
            location=self.location
        )


class Dependency(BaseModel):
    source: Optional[PackageVersionIdentifier] = None
    target: PackageVersionIdentifier
    version_constraint: SemVerConstraint


class ResolvedDependency(BaseModel):
    source: Optional[PackageVersionIdentifier] = None
    target_package: PackageIdentifier
    target_version: str
    version_constraint: SemVerConstraint
    resolved_version: str
