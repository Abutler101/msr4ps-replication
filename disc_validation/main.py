import copy
import csv
from pathlib import Path
from typing import Callable, List, Tuple, Any, Dict

import networkx as nx
from loguru import logger

import disc_validation.criticality_measures as cm


def drop_top_x_pct(
    graph: nx.Graph, criticality_func: Callable[[nx.Graph], List[Tuple[Any, float]]], cut_pct: float
) -> nx.Graph:
    """
    Returns a copy of the given graph with the top cut_pct nodes, as determined by criticality_func.
    cut_pct should be a float between 0-1
    """
    node_scores = criticality_func(graph)
    node_scores.sort(key=lambda entry: entry[1], reverse=True)
    cutoff_idx = int(cut_pct * graph.number_of_nodes())
    trimmed_graph = copy.deepcopy(graph)
    trimmed_graph.remove_nodes_from([entry[0] for entry in node_scores[:cutoff_idx]])
    return trimmed_graph


def main():
    cut_pct = 0.05
    graph_sizes = [50, 100, 250, 500, 750, 1000, 2500, 5000]
    output_dir = Path(__file__).parent.joinpath("output")
    output_dir.mkdir(exist_ok=True)

    for graph_size in graph_sizes:
        logger.info(f"━━━━━━━━━━━━━━━━━━━━\t{graph_size} Node Graph\t━━━━━━━━━━━━━━━━━━━━")
        target_graph = nx.scale_free_graph(n=graph_size)
        connectivity_before = nx.average_node_connectivity(target_graph)
        logger.info(f"Avg Node Connectivity Baseline: {connectivity_before:.3f}")
        results: Dict[str, Tuple[float, float]] = {"Initial": (connectivity_before, 0.0)}

        for label, crit_measure in cm.CRITICALITY_MEASURES.items():
            trimmed_graph = drop_top_x_pct(target_graph, crit_measure, cut_pct)
            connectivity_after = nx.average_node_connectivity(trimmed_graph)
            pct_diff = ((connectivity_after - connectivity_before)/connectivity_before) * 100
            logger.info(f"Avg Node Connectivity After {label}: {connectivity_after:.3f} ({pct_diff:.3f}% drop)")
            results[label] = (connectivity_after, pct_diff)

        with output_dir.joinpath(f"sf_{graph_size}_diffs.csv").open("w") as csv_file:
            writer = csv.writer(csv_file)
            for key, value in results.items():
                writer.writerow([key, value[0], value[1]])


if __name__ == '__main__':
    main()
