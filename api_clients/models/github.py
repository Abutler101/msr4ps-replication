from typing import Optional

from pydantic import BaseModel


class VersionInfo(BaseModel):
    vcs_tag: Optional[str] = None
    change_notes: Optional[str] = None
