import datetime
from typing import List, Optional, Union, Dict, TypeVar

from pydantic import BaseModel

from shared_models.packages import PackageLanguage


VersionString = TypeVar("VersionString", bound=str)


class PackageInfo(BaseModel):
    name: str
    known_versions: List[str]
    language: PackageLanguage
    description: Optional[str] = None
    licenses: Optional[Union[str, List[str]]] = None
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    author: Optional[str] = None
    maintainers: Optional[List[str]] = None
    release_times: Optional[Dict[str, datetime.datetime]] = None
