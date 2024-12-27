from typing import Optional, Dict, Any, Literal, List, Union

from loguru import logger
from neo4j import GraphDatabase, Driver, Query, Session, exceptions
from neo4j.exceptions import ConstraintError

from storage_interface.config import Neo4jConfig
import shared_models.graph_models as gm
import shared_models.packages as pm
from storage_interface.graph.internal_models import QueryResult


class Neo4jClient:
    db_config: Neo4jConfig
    db_driver: Driver
    DB_MAP: Dict[pm.PackageLocation, str] = {pm.PackageLocation.PYPI: "pypi", pm.PackageLocation.NPM: "npm"}

    def __init__(self, conf: Neo4jConfig = Neo4jConfig()):
        self.db_config = conf
        uri = f"neo4j://{self.db_config.host}:{self.db_config.port}"
        logger.info(f"Targeting neo4j on URI {uri}")
        self.db_driver = GraphDatabase.driver(uri=uri, auth=("neo4j", self.db_config.password))
        logger.info(f"DB Auth: {self.db_driver.verify_authentication()}")
        self._create_dbs()

    def __del__(self):
        self.db_driver.close()

    """
    Cypher Syntax:
    Pulled from: https://neo4j.com/docs/cypher-manual/current/clauses/create/
    Style Guide: https://neo4j.com/developer/cypher/style-guide/
    
    Labels ≈ Node Type
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Read Queries ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    def package_version_exists(self, target: pm.PackageVersionIdentifier) -> bool:
        target_db = self.DB_MAP[target.location]
        query_text = ("MATCH (p:Package {name: $name})-[:Released]->(pv:PackageVersion {version: $version})"
                      "WITH COUNT(pv) > 0  as node_exists "
                      "RETURN node_exists"
                     )
        query_params = {"version": target.version, "name": target.name.lower()}
        response = self._run_query(Query(query_text), query_params, target_db)
        exists = response.values[0][0]
        return exists

    def package_exists(self, target: Union[pm.PackageIdentifier, pm.PackageVersionIdentifier]) -> bool:
        target_db = self.DB_MAP[target.location]
        query_text = ("MATCH (p:Package {name: $name})"
                      "WITH COUNT(p) > 0  as node_exists "
                      "RETURN node_exists"
                      )
        query_params = {"name": target.name.lower()}
        response = self._run_query(Query(query_text), query_params, target_db)
        exists = response.values[0][0]
        return exists

    def read_package_node(
        self, target: Union[pm.PackageIdentifier, pm.PackageVersionIdentifier]
    ) -> Optional[gm.Package]:
        target_db = self.DB_MAP[target.location]
        query_text = ("MATCH (p:Package {name: $name})"
                      "RETURN p"
                      )
        query_params = {"name": target.name.lower()}
        response = self._run_query(Query(query_text), query_params, target_db)
        logger.debug(f"reading package response: {response.values}")
        if len(response.values) == 0:
            return None
        package_node = response.values[0][0]
        return gm.Package.from_node(package_node)

    def read_package_version_release_edge(self, target: pm.PackageVersionIdentifier) -> Optional[gm.ReleaseEdge]:
        target_db = self.DB_MAP[target.location]
        query_text = ("MATCH (p:Package {name: $name})-[r:Released]->(pv:PackageVersion {version: $version})"
                      "RETURN p, r, pv"
                      )
        query_params = {"name": target.name.lower(), "version": target.version}
        response = self._run_query(Query(query_text), query_params, target_db)
        logger.debug(f"reading package version response: {response.values}")
        if (response.values is None or len(response.values) == 0) or len(response.values[0]) != 3:
            return None
        package_node, release_relation, version_node = response.values[0]
        return gm.ReleaseEdge.from_relation(release_relation)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Insert Nodes Without Edges ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    def insert_package(self, package: gm.Package, database: str) -> Optional[QueryResult]:
        """
        Inserts a standalone package
        """
        query_text = ("MERGE (package: Package {name:$name, language:$language})\n"
                      "ON CREATE\n"
                      "    SET package.description = $description\n"
                      "    SET package.license = $license\n"
                      "    SET package.homepage_url = $homepage_url\n"
                      "    SET package.repo_url = $repo_url\n"
                      "    SET package.author = $author\n"
                      "    SET package.maintainer = $maintainer\n"
                      "    SET package.indexed_at = timestamp()\n"
                     )
        query_params: Dict[str, Any] = package.graph_prop_dict()
        try:
            response = self._run_query(Query(query_text), query_params, database)
        except ConstraintError as err:
            logger.debug(f"{err.message}")
            return None
        return response

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Insert Nodes With Edges ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    def insert_package_release(self, release: gm.ReleaseEdge, database: str) -> Optional[QueryResult]:
        """
        Inserts a package, a version of that package, and an edge connecting the two into the target db
        """
        query_text = ("MERGE (package: Package {name:$name, language:$language})\n"
                      "ON CREATE\n"
                      "    SET package.description = $description\n"
                      "    SET package.license = $license\n"
                      "    SET package.homepage_url = $homepage_url\n"
                      "    SET package.repo_url = $repo_url\n"
                      "    SET package.author = $author\n"
                      "    SET package.maintainer = $maintainer\n"
                      "    SET package.indexed_at = timestamp()\n"
                      "MERGE (package)-[release: Released]->(package_version: PackageVersion {version:$version})\n"
                      "ON CREATE\n"
                      "    SET package_version.change_notes = $change_notes\n"
                      "    SET package_version.vcs_tag = $vcs_tag\n"
                      "    SET package_version.indexed_at = timestamp()\n"
                      "    SET release.released_at = $released_at\n"
                     )
        query_params: Dict[str, Any] = release.graph_prop_dict()
        try:
            response = self._run_query(Query(query_text), query_params, database)
        except ConstraintError as err:
            logger.debug(f"{err.message}")
            return None
        return response

    def insert_git_snapshot(self, vcs_capture: gm.CapturedEdge, database: str) -> Optional[QueryResult]:
        """
        inserts a GitSnapshot for an existing Package and connects the two with an edge
        """
        query_text = (
            "MATCH (tgt_package:Package {name:$name})\n"
            "MERGE (git_capture: GitSnapshot)-[capture_edge: Captured]->(tgt_package)\n"
            "ON CREATE\n"
            "    SET git_capture.stars = $stars\n"
            "    SET git_capture.forks = $forks\n"
            "    SET git_capture.watchers = $watchers\n"
            "    SET git_capture.issue_count = $issues\n"
            "    SET git_capture.contributor_count = $contributors\n"
            "    SET git_capture.active_contributor_count = $active_contributors\n"
            "    SET git_capture.ci_cd = $ci_cd\n"
            "    SET git_capture.indexed_at = timestamp()\n"
            "    SET capture_edge.captured_at = $captured_at\n"
        )
        query_params: Dict[str, Any] = vcs_capture.graph_prop_dict()
        try:
            response = self._run_query(Query(query_text), query_params, database)
        except ConstraintError as err:
            logger.debug(f"{err.message}")
            return None
        return response

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Insert Edges ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    def insert_dep_relations(
        self, resolved_dep: pm.ResolvedDependency, database: str
    ) -> Optional[QueryResult]:
        """
        Inserts outbound edges from a PackageVersion to a Package, and from the PackageVersion to a release of the Package.
        Assumes that the dependent PackageVersion is already present and well formed.
        Assumes that the dependee Package and PackageVersion are already present and well formed.
        """
        if resolved_dep.source is None:
            raise ValueError("Dependency is missing source package")

        query_text: Literal = (
            "MATCH (:Package {name:$dependent_name})-[: Released]->(dependent: PackageVersion {version:$dependent_version})\n"
            "MATCH (tgt_package: Package {name:$target_name})-[: Released]->(tgt_version: PackageVersion {version:$resolved_version})\n"
            "MERGE (dependent)-[dep_edge: DependsOn]->(tgt_package)\n"
            "ON CREATE\n"
            "    SET dep_edge.version = $unresolved_version\n"
            "    SET dep_edge.constraint = $version_constraint\n"
            "MERGE (dependent)-[resolved_dep_edge: HasResolvedDependencyOn]->(tgt_version)\n"
        )
        query_params: Dict[str, Any] = {
            "dependent_name": resolved_dep.source.name.lower(),
            "dependent_version": resolved_dep.source.version,
            "target_name": resolved_dep.target_package.name.lower(),
            "unresolved_version": resolved_dep.target_version,
            "version_constraint": resolved_dep.version_constraint,
            "resolved_version": resolved_dep.resolved_version,
        }
        try:
            response = self._run_query(Query(query_text), query_params, database)
        except ConstraintError as err:
            logger.debug(f"{err.message}")
            return None
        return response

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Internal methods ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ #
    def _create_dbs(self):
        session = self.db_driver.session()
        try:
            session.run("CREATE DATABASE pypi")
            session.run("USE pypi\n"
                        "CREATE CONSTRAINT package_name\n"
                        "FOR (package:Package) REQUIRE package.name IS UNIQUE")
        except exceptions.DatabaseError as err:
            if "already exists" not in err.message:
                raise err

        try:
            session.run("CREATE DATABASE npm")
            session.run("USE npm\n"
                        "CREATE CONSTRAINT package_name\n"
                        "FOR (package:Package) REQUIRE package.name IS UNIQUE")
        except exceptions.DatabaseError as err:
            if "already exists" not in err.message:
                raise err

        finally:
            session.close()

    def _run_query(
        self,
        cypher_query: Query,
        query_params: Dict[str, Any],
        database: Optional[str] = None,
        fetch_size: int = 1000
    ) -> QueryResult:
        result: QueryResult
        logger.debug(f"Running Query: {cypher_query.text}, against {'default' if database is None else database} db")
        with self.db_driver.session(database=database, fetch_size=fetch_size) as session:
            try:
                response = session.run(cypher_query, query_params)
                result = QueryResult(values=response.values(), keys=response.keys(), summary=None)
                result.summary = response.consume()
            finally:
                # docs say will run close then re-raise any error
                # https://docs.python.org/3/reference/compound_stmts.html#finally
                session.close()
        return result
