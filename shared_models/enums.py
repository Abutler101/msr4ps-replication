from enum import Enum


class SemVerConstraint(str, Enum):
    EXACT = "=="
    GREATER_THAN_EQUAL_TO = ">="
    LESS_THAN_EQUAL_TO = "<="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    APPROXIMATELY = "~"  # Semantic versioning syntax https://github.com/npm/node-semver#tilde-ranges-123-12-1
    COMPATIBLE_WITH = "^"  # Semantic versioning syntax https://github.com/npm/node-semver#caret-ranges-123-025-004
    ANY = "*"