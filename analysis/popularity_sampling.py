from pathlib import Path

import pandas as pd
from neo4j import Query

from storage_interface.graph.neo4j_client import Neo4jClient

OUTPUT_DIR = Path(__file__).parent.joinpath("output")

FORKS_QUERY = Query(
    "MATCH (p:Package)<-[c:Captured]-(g:GitSnapshot)\n"
    "WITH p,g,c\n"
    "RETURN p.name as package_name, g.forks as forks\n"
    "ORDER BY g.forks DESC\n"
)


def bin_and_sample(target: str) -> pd.DataFrame:
    neo_client = Neo4jClient()
    raw_response = neo_client._run_query(FORKS_QUERY, dict(), database=target).values
    fork_scores = pd.DataFrame(raw_response, columns=["package_name", "forks"])

    fork_scores["bin"], bins = pd.cut(fork_scores.forks, bins=20, retbins=True)
    binned = fork_scores.groupby(["bin"])
    non_empty_groups = {group: data for group, data in binned if not data.empty}

    samples = []
    for bin, entries in non_empty_groups.items():
        sample = entries.sample(n=15, replace=True)
        samples.append(sample)

    sampled = pd.concat(samples).reset_index(drop=True)
    sampled.to_csv(OUTPUT_DIR.joinpath(f"{target}/sampled_fork_packs.csv"))
    return sampled


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.joinpath("npm").mkdir(exist_ok=True)
    OUTPUT_DIR.joinpath("pypi").mkdir(exist_ok=True)
    npm_sampled = bin_and_sample("npm")
    pypi_sampled = bin_and_sample("pypi")


if __name__ == '__main__':
    main()
