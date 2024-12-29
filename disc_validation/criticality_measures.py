import random
from typing import List, Tuple, Any, Dict, Callable

import networkx as nx


def disc_score_nodes(g: nx.Graph) -> List[Tuple[Any, float]]:
    """Assumes g is a directed graph"""
    DISC_THRESHOLD = 2
    all_nodes_out_degs = g.out_degree
    all_nodes_isolating_coefficents = []
    for node in g:
        all_inbound_neighbors = list(g.predecessors(node))
        inbound_neighbor_count = len([n for n in all_inbound_neighbors if all_nodes_out_degs[n] <= DISC_THRESHOLD])
        all_nodes_isolating_coefficents.append(inbound_neighbor_count)
    all_nodes_disc_scores = [(n, all_nodes_out_degs[n] * all_nodes_isolating_coefficents[n]) for n in range(len(g.nodes))]
    return all_nodes_disc_scores


def degree_cent_score_nodes(g: nx.Graph) -> List[Tuple[Any, float]]:
    degree_scores = nx.degree_centrality(g)
    return [(n, degree_scores[n]) for n in g]


def between_cent_score_nodes(g: nx.Graph) -> List[Tuple[Any, float]]:
    betweenness_scores = nx.betweenness_centrality(g)
    return [(n, betweenness_scores[n]) for n in g]


def closeness_cent_score_nodes(g: nx.Graph) -> List[Tuple[Any, float]]:
    return [(n, nx.closeness_centrality(g, n)) for n in g]


def random_score_nodes(g: nx.Graph) -> List[Tuple[Any, float]]:
    return [(n, random.random()) for n in g]


CRITICALITY_MEASURES: Dict[str, Callable] = {
    "DISC": disc_score_nodes,
    "Degree_Centrality": degree_cent_score_nodes,
    "Betweenness_Centrality": between_cent_score_nodes,
    "Closeness_Centrality": closeness_cent_score_nodes,
    "Random": random_score_nodes
}
