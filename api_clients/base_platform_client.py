import abc
import re
from functools import cmp_to_key
from typing import List, Optional, Tuple

from loguru import logger
from semver import Version

from data_collection_worker.api_clients.models.platform_client import PackageInfo, VersionString
from shared_models.enums import SemVerConstraint
from shared_models.packages import Dependency


class BasePlatformClient(abc.ABC):

    @abc.abstractmethod
    def __init__(self, config):
        pass

    @abc.abstractmethod
    def get_package_info(self, package_name: str) -> PackageInfo:
        pass

    @abc.abstractmethod
    def get_package_requirements(
        self, package_name: str, target_version: VersionString
    ) -> List[Dependency]:
        pass

    def resolve_dependency(
        self, package_name: str, target_version: VersionString, version_constraint: SemVerConstraint
    ) -> Optional[VersionString]:
        package_info = self.get_package_info(package_name)
        if package_info is None:
            return None
        available_versions = package_info.known_versions

        if version_constraint is SemVerConstraint.EXACT:
            if target_version not in available_versions:
                return None
            return target_version

        try:
            semver_target = Version.parse(target_version)
            semver_available = [Version.parse(v) for v in available_versions]
        except ValueError as err:
            logger.info(
                f"Looks like {package_name} doesn't use semver compliant version format. Target: {target_version}"
            )
            return self._non_compliant_resolve(target_version, version_constraint, available_versions)

        return self._semver_compliant_resolve(semver_target, version_constraint, semver_available)

    @staticmethod
    def _semver_compliant_resolve(
        target: Version, constraint: SemVerConstraint, available_vers: List[Version]
    ) -> Optional[VersionString]:
        sorted_available = sorted(available_vers)
        if constraint is SemVerConstraint.GREATER_THAN_EQUAL_TO:
            # Most recent >= than target
            if sorted_available[-1] >= target:
                return str(sorted_available[-1])
            else:
                return None

        elif constraint is SemVerConstraint.LESS_THAN_EQUAL_TO:
            # Most recent <= than target
            candidate_version_idx = 0
            while sorted_available[candidate_version_idx] <= target and candidate_version_idx < len(sorted_available)-1:
                if sorted_available[candidate_version_idx+1] > target:
                    # The next version fails the constraint,
                    # so the candidate is the most recent one that meets constraint
                    return str(sorted_available[candidate_version_idx])
                candidate_version_idx += 1
            return str(sorted_available[candidate_version_idx])

        elif constraint is SemVerConstraint.GREATER_THAN:
            # Most recent > than target
            if sorted_available[-1] > target:
                return str(sorted_available[-1])
            else:
                return None

        elif constraint is SemVerConstraint.LESS_THAN:
            # Most recent < than target
            candidate_version_idx = 0
            while sorted_available[candidate_version_idx] < target and candidate_version_idx < len(sorted_available)-1:
                if sorted_available[candidate_version_idx+1] >= target:
                    # The next version fails the constraint,
                    # so the candidate is the most recent one that meets constraint
                    return str(sorted_available[candidate_version_idx])
                candidate_version_idx += 1
            return str(sorted_available[candidate_version_idx])

        elif constraint is SemVerConstraint.APPROXIMATELY:
            # Most recent with same Major and Minor version - matches fixed.fixed.X where X can be any value
            candidates = [x for x in sorted_available if x.major == target.major and x.minor == target.minor]
            if len(candidates) == 0:
                return None
            return str(candidates[-1])

        elif constraint is SemVerConstraint.COMPATIBLE_WITH:
            # Most recent with same Major version - matches fixed.X.Y where X and Y can be any values
            candidates = [x for x in sorted_available if x.major == target.major]
            if len(candidates) == 0:
                return None
            return str(candidates[-1])

        elif constraint is SemVerConstraint.ANY:
            # Most recent
            return str(sorted_available[-1])

        else:
            return None

    def _non_compliant_resolve(
        self, target: VersionString, constraint: SemVerConstraint, available_vers: List[VersionString]
    ) -> Optional[VersionString]:
        normalised_target = self._normalise_string_version(target, "0.0.0")
        sorted_available: List[Tuple[List[int], str]] = sorted(
            [(self._normalise_string_version(x, "0.0.0"), x) for x in available_vers],
            key=cmp_to_key(self._version_comp)
        )

        if constraint is SemVerConstraint.GREATER_THAN_EQUAL_TO:
            # Most recent >= than target
            if self._version_comp_geq(sorted_available[-1][0], normalised_target):
                return sorted_available[-1][1]
            else:
                return None

        elif constraint is SemVerConstraint.LESS_THAN_EQUAL_TO:
            # Most recent <= than target
            candidate_version_idx = 0
            while (self._version_comp_leq(sorted_available[candidate_version_idx][0], normalised_target) and
                   candidate_version_idx < len(sorted_available)-1):
                if self._version_comp_gt(sorted_available[candidate_version_idx+1][0], normalised_target):
                    # The next version fails the constraint,
                    # so the candidate is the most recent one that meets constraint
                    return sorted_available[candidate_version_idx][1]
                candidate_version_idx += 1
            return sorted_available[candidate_version_idx][1]

        elif constraint is SemVerConstraint.GREATER_THAN:
            # Most recent > than target
            if self._version_comp_gt(sorted_available[-1][0], normalised_target):
                return sorted_available[-1][1]
            else:
                return None

        elif constraint is SemVerConstraint.LESS_THAN:
            # Most recent < than target
            candidate_version_idx = 0
            while (self._version_comp_lt(sorted_available[candidate_version_idx][0], normalised_target) and
                   candidate_version_idx < len(sorted_available)-1):
                if self._version_comp_geq(sorted_available[candidate_version_idx+1][0], normalised_target):
                    # The next version fails the constraint,
                    # so the candidate is the most recent one that meets constraint
                    return sorted_available[candidate_version_idx][1]
                candidate_version_idx += 1
            return sorted_available[candidate_version_idx][1]

        elif constraint is SemVerConstraint.APPROXIMATELY:
            candidates = [x for x in sorted_available if x[0][0] == normalised_target[0] and x[0][1] == normalised_target[1]]
            if len(candidates) == 0:
                return None
            return candidates[-1][1]

        elif constraint is SemVerConstraint.COMPATIBLE_WITH:
            candidates = [x for x in sorted_available if x[0][0] == normalised_target[0]]
            if len(candidates) == 0:
                return None
            return candidates[-1][1]

        elif constraint is SemVerConstraint.ANY:
            return sorted_available[-1][1]

        else:
            return None

    @staticmethod
    def _normalise_string_version(
        version: VersionString, reference_version: Optional[VersionString] = None
    ) -> List[int]:
        """
        Takes in a . seperated version string and transforms it to a list of ints.
        If reference version is given, this will be used to set the number of elements in the resulting list
        version="1.2.3.4", reference_version="4.5.6" -> result=[1,2,3]
        version="1.2.3.4.6", reference_version=None -> result=[1,2,3,4,6]
        """
        element_count = len(version.split("."))
        if reference_version is not None:
            element_count = len(reference_version.split("."))
        split_version = [
            int(re.sub("[^0-9]","", x)) for x in version.split(".")
            if len(re.sub("[^0-9]","", x)) > 0
        ]
        while len(split_version) < element_count:
            split_version.append(0)
        return split_version[:element_count]

    def _version_comp(self, v1: List[int], v2:List[int]) -> int:
        """
        Compares v1 and v2.
        if v1 < v2, return -1
        if v1 == v2, return 0
        if v1 > v2, return 1
        """
        while len(v1) > len(v2):
            v2.append(0)
        while len(v2) > len(v1):
            v1.append(0)
        if self._version_comp_gt(v1, v2):
            return 1
        if self._version_comp_lt(v1, v2):
            return -1
        return 0

    @staticmethod
    def _version_comp_eq(v1: List[int], v2: List[int]) -> bool:
        return v1 == v2

    @staticmethod
    def _version_comp_gt(v1: List[int], v2:List[int]) -> bool:
        while len(v1) > len(v2):
            v2.append(0)
        while len(v2) > len(v1):
            v1.append(0)
        for idx, value in enumerate(v1):
            if value > v2[idx]:
                return True
            if value < v2[idx]:
                return False

    @staticmethod
    def _version_comp_geq(v1: List[int], v2:List[int]) -> bool:
        while len(v1) > len(v2):
            v2.append(0)
        while len(v2) > len(v1):
            v1.append(0)
        for idx, value in enumerate(v1):
            if value >= v2[idx]:
                return True
            if value < v2[idx]:
                return False

    @staticmethod
    def _version_comp_lt(v1: List[int], v2:List[int]) -> bool:
        while len(v1) > len(v2):
            v2.append(0)
        while len(v2) > len(v1):
            v1.append(0)
        for idx, value in enumerate(v1):
            if value < v2[idx]:
                return True
            if value > v2[idx]:
                return False

    @staticmethod
    def _version_comp_leq(v1: List[int], v2:List[int]) -> bool:
        while len(v1) > len(v2):
            v2.append(0)
        while len(v2) > len(v1):
            v1.append(0)
        for idx, value in enumerate(v1):
            if value <= v2[idx]:
                return True
            if value > v2[idx]:
                return False
