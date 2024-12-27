from pathlib import Path

from neo4j import Query
import pandas as pd

from storage_interface.graph.neo4j_client import Neo4jClient

OUTPUT_DIR = Path(__file__).parent.joinpath("output")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.joinpath("npm").mkdir(exist_ok=True)
    OUTPUT_DIR.joinpath("pypi").mkdir(exist_ok=True)
    neo_client = Neo4jClient()
    degree_query = Query(
        "MATCH (package:Package)\n"
        "CALL {\n"
        "    WITH package\n"
        "    WITH apoc.node.degree(package, '<DependsOn') as inDegree\n"
        "    RETURN inDegree\n"
        "}\n"
        "RETURN package.name as name, inDegree\n"
        "ORDER BY inDegree DESC"
    )

    # Get the in-degree for each package of the 2 ecosystems
    npm_degs_raw = neo_client._run_query(degree_query, dict(), database="npm").values
    pypi_degs_raw = neo_client._run_query(degree_query, dict(), database="pypi").values
    # Parse query result to Dataframe where each row is: package name, in degree
    npm_degs = pd.DataFrame(npm_degs_raw)
    pypi_degs = pd.DataFrame(pypi_degs_raw)
    # Write to csvs in output dir
    npm_degs.to_csv(OUTPUT_DIR.joinpath("npm/degrees.csv"), index=False, header=False)
    pypi_degs.to_csv(OUTPUT_DIR.joinpath("pypi/degrees.csv"), index=False, header=False)

    # Gen in degree distributions for both ecosystems
    npm_distrib = npm_degs[1].value_counts().sort_index()
    pypi_distrib = pypi_degs[1].value_counts().sort_index()
    # Write distribs to csvs in output dir
    npm_distrib.to_csv(OUTPUT_DIR.joinpath("npm/deg_distrib.csv"), index=True, header=False)
    pypi_distrib.to_csv(OUTPUT_DIR.joinpath("pypi/deg_distrib.csv"), index=True, header=False)


if __name__ == '__main__':
    main()
