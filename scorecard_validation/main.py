from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from loguru import logger
from neo4j import Query
from pydantic import BaseModel

from scorecard_validation.bandit_on_repo import bandit_on_repo
from scorecard_validation.count_loc import count_loc
from scorecard_validation.ossf_on_repo import ossf_on_repo
from scorecard_validation.utils import clone_repo, extract_repo_id
from storage_interface.graph.neo4j_client import Neo4jClient


OUTPUT_DIR = Path(__file__).parent.joinpath("output")
RANDOM_SAMPLE_QUERY = Query(
    "MATCH (package:Package)\n"
    "RETURN package.name as name, package.repo_url as url, rand() as r\n"
    "ORDER BY r\n"
    "LIMIT $package_count"
)


class SecurityScores(BaseModel):
    ossf_scorecard: float
    vuln_density: float


def calc_scores(repo_url: str) -> SecurityScores:
    repo_id = extract_repo_id(repo_url)
    clone_repo(repo_id)
    logger.debug(f"Cloned {repo_url} into dir: target-repo")

    logger.info(f"Calculating Vuln Density (static analysis vuln count / KLoC) for {repo_url}")
    kloc_count = count_loc()/1000
    vuln_count = bandit_on_repo()
    vuln_density = vuln_count / kloc_count
    logger.debug(f"Vuln Density = {vuln_count}/{kloc_count} = {vuln_density}")

    logger.info(f"Running OSSF Scorecard against {repo_id}")
    ossf_scorecard_score = ossf_on_repo(repo_id)
    logger.debug(f"ossf scorecard score = {ossf_scorecard_score}")
    return SecurityScores(ossf_scorecard=ossf_scorecard_score, vuln_density=vuln_density)


def random_sample_pypi_graph(sample_size: int) -> pd.DataFrame:
    neo_client = Neo4jClient()
    raw_response = neo_client._run_query(
        RANDOM_SAMPLE_QUERY, {"package_count": sample_size}, database="pypi"
    ).values
    sampled_packages = pd.DataFrame(raw_response, columns=["name", "url", "r"]).drop("r", axis=1)
    # Ignore packages that are missing a VCS url or that aren't hosted on GitHub
    sampled_packages = sampled_packages.loc[sampled_packages['url'] != "~MISSING~"]
    sampled_packages = sampled_packages[sampled_packages['url'].str.contains("github")]
    return sampled_packages


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    target_repos = random_sample_pypi_graph(300)
    results: List[Tuple[str, float, float]] = []
    for _, row in target_repos.iterrows():
        try:
            scores=calc_scores(row["url"])
        except Exception as err:
            logger.warning(f"Scoring {row['name']} gave error: {err}")
            continue
        result=(row["name"], scores.ossf_scorecard, scores.vuln_density)
        results.append(result)
    scored_sample = pd.DataFrame(results, columns=["name", "ossf_scorecard", "vuln_density"])
    scored_sample.to_csv(OUTPUT_DIR.joinpath("security_scores.csv"), index=False)


if __name__ == '__main__':
    main()
