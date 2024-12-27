from pathlib import Path

import pandas as pd
from neo4j import Query

from storage_interface.graph.neo4j_client import Neo4jClient

OUTPUT_DIR = Path(__file__).parent.joinpath("output")
DISC_QUERY = Query(
    "MATCH (bp:Package)\n"
    "WITH bp, SIZE(COLLECT{\n"
    "    MATCH (bp)-[:Released]->(sv:PackageVersion)-[dd:DependsOn]->(deptarg:Package)\n"
    "    WITH DISTINCT deptarg.name as dependency\n"
    "    RETURN dependency\n"
    "}) as bpOutDegree\n"
    "WITH bp, bpOutDegree, SIZE(COLLECT {\n"
    "    MATCH (np:Package)-[:Released]->(sv:PackageVersion)-[dd:DependsOn]->(bp)\n"
    "    WITH np, SIZE(COLLECT{\n"
    "        MATCH (np)-[:Released]->(sv:PackageVersion)-[dd:DependsOn]->(deptarg:Package)\n"
    "        WITH DISTINCT deptarg.name as dependency\n"
    "        RETURN dependency\n"
    "    }) as npOutDegree\n"
    "    WHERE npOutDegree <= 2 //Degree threshold\n"
    "    RETURN distinct np.name\n"
    "}) as isolatingCoefficient\n"
    "RETURN bp.name as package, bpOutDegree, isolatingCoefficient, bpOutDegree*isolatingCoefficient as  isolatingCentrality\n"
    "ORDER BY isolatingCentrality DESC"
)


def bin_and_sample(target: str) -> pd.DataFrame:
    neo_client = Neo4jClient()
    disc_raw = neo_client._run_query(DISC_QUERY, dict(), database=target).values
    isolating_scores = pd.DataFrame(
        disc_raw, columns=["package_name", "outDegree", "isolatingCoefficient", "isolatingCentrality"]
    )

    isolating_scores["bin"], bins = pd.cut(isolating_scores.isolatingCentrality, bins=20, retbins=True)
    binned = isolating_scores.groupby(["bin"])
    non_empty_groups = {group: data for group, data in binned if not data.empty}

    samples = []
    for bin, entries in non_empty_groups.items():
        sample = entries.sample(n=15, replace=True)
        samples.append(sample)

    sampled = pd.concat(samples).reset_index(drop=True)
    sampled.to_csv(OUTPUT_DIR.joinpath(f"{target}/sampled_disc_packs.csv"))
    return sampled


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.joinpath("npm").mkdir(exist_ok=True)
    OUTPUT_DIR.joinpath("pypi").mkdir(exist_ok=True)
    npm_sampled = bin_and_sample("npm")
    pypi_sampled = bin_and_sample("pypi")


if __name__ == '__main__':
    main()
