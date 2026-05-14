from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "data" / "processed" / "clean_creator_dataset.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "docs" / "sna_project_outputs"
DEFAULT_NOTEBOOK = BASE_DIR / "docs" / "sna_creator_network.ipynb"

RANDOM_SEED = 42
CATEGORY_WEIGHT = 0.75
HASHTAG_WEIGHT = 0.25
SIMILARITY_THRESHOLD = 0.30
MAX_SHARED_TAGS = 5


@dataclass(frozen=True)
class CreatorRecord:
    username: str
    source_type: str
    source_file: str
    posts: int
    followers: float
    follower_segment: str
    avg_likes: float
    avg_comments: float
    categories: tuple[str, ...]
    top_hashtags: tuple[str, ...]
    primary_category: str
    account_type: str
    account_confidence: float
    creator_score: float
    business_score: float
    media_score: float


def split_field(value: object) -> tuple[str, ...]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return tuple()
    parts = [part.strip() for part in str(value).split(",")]
    return tuple(part for part in parts if part and part.lower() != "nan")


def load_creator_records(csv_path: Path) -> list[CreatorRecord]:
    df = pd.read_csv(csv_path)
    records: list[CreatorRecord] = []

    for row in df.to_dict(orient="records"):
        categories = split_field(row.get("categories"))
        hashtags = split_field(row.get("top_hashtags"))
        records.append(
            CreatorRecord(
                username=str(row.get("username", "")).strip(),
                source_type=str(row.get("source_type", "")).strip(),
                source_file=str(row.get("source_file", "")).strip(),
                posts=int(row.get("posts", 0) or 0),
                followers=float(row.get("followers", 0) or 0),
                follower_segment=str(row.get("follower_segment", "unknown")).strip() or "unknown",
                avg_likes=float(row.get("avg_likes", 0) or 0),
                avg_comments=float(row.get("avg_comments", 0) or 0),
                categories=categories,
                top_hashtags=hashtags,
                primary_category=categories[0] if categories else "unknown",
                account_type=str(row.get("account_type", "unknown")).strip() or "unknown",
                account_confidence=float(row.get("account_confidence", 0) or 0),
                creator_score=float(row.get("creator_score", 0) or 0),
                business_score=float(row.get("business_score", 0) or 0),
                media_score=float(row.get("media_score", 0) or 0),
            )
        )

    return records


def jaccard_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def compute_edge_payload(left: CreatorRecord, right: CreatorRecord) -> dict[str, object]:
    category_overlap = jaccard_similarity(left.categories, right.categories)
    hashtag_overlap = jaccard_similarity(left.top_hashtags, right.top_hashtags)
    weight = CATEGORY_WEIGHT * category_overlap + HASHTAG_WEIGHT * hashtag_overlap

    shared_categories = sorted(set(left.categories) & set(right.categories))
    shared_hashtags = sorted(set(left.top_hashtags) & set(right.top_hashtags))[:MAX_SHARED_TAGS]

    return {
        "weight": round(weight, 4),
        "distance": round(1.0 / (weight + 1e-6), 6),
        "category_overlap": round(category_overlap, 4),
        "hashtag_overlap": round(hashtag_overlap, 4),
        "shared_categories": ",".join(shared_categories),
        "shared_hashtags": ",".join(shared_hashtags),
    }


def build_creator_graph(records: list[CreatorRecord]) -> nx.Graph:
    graph = nx.Graph(name="creator_similarity_network")

    for record in records:
        graph.add_node(
            record.username,
            source_type=record.source_type,
            source_file=record.source_file,
            posts=record.posts,
            followers=record.followers,
            follower_segment=record.follower_segment,
            avg_likes=round(record.avg_likes, 2),
            avg_comments=round(record.avg_comments, 2),
            categories=",".join(record.categories),
            primary_category=record.primary_category,
            top_hashtags=",".join(record.top_hashtags),
            account_type=record.account_type,
            account_confidence=round(record.account_confidence, 2),
            creator_score=round(record.creator_score, 2),
            business_score=round(record.business_score, 2),
            media_score=round(record.media_score, 2),
        )

    for left, right in itertools.combinations(records, 2):
        edge_payload = compute_edge_payload(left, right)
        if edge_payload["weight"] >= SIMILARITY_THRESHOLD:
            graph.add_edge(left.username, right.username, **edge_payload)

    return graph


def largest_connected_component(graph: nx.Graph) -> nx.Graph:
    component_nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(component_nodes).copy()


def power_iteration_pagerank(
    graph: nx.Graph,
    alpha: float = 0.85,
    weight_attr: str = "weight",
    max_iter: int = 500,
    tol: float = 1e-9,
) -> dict[str, float]:
    nodes = list(graph.nodes())
    node_count = len(nodes)
    node_index = {node: index for index, node in enumerate(nodes)}
    matrix = np.zeros((node_count, node_count), dtype=float)

    for node in nodes:
        column_index = node_index[node]
        neighbors = list(graph.neighbors(node))
        if not neighbors:
            matrix[:, column_index] = 1.0 / node_count
            continue

        weights = np.array([graph[node][neighbor].get(weight_attr, 1.0) for neighbor in neighbors], dtype=float)
        total = weights.sum()
        if total <= 0:
            matrix[:, column_index] = 1.0 / node_count
            continue

        for neighbor, weight in zip(neighbors, weights):
            matrix[node_index[neighbor], column_index] = weight / total

    scores = np.full(node_count, 1.0 / node_count, dtype=float)
    teleport = np.full(node_count, 1.0 / node_count, dtype=float)

    for _ in range(max_iter):
        next_scores = alpha * (matrix @ scores) + (1.0 - alpha) * teleport
        if np.abs(next_scores - scores).sum() < tol:
            scores = next_scores
            break
        scores = next_scores

    return {node: float(scores[node_index[node]]) for node in nodes}


def build_node_table(graph: nx.Graph) -> pd.DataFrame:
    component_map: dict[str, int] = {}
    for component_id, component in enumerate(sorted(nx.connected_components(graph), key=len, reverse=True), start=1):
        for node in component:
            component_map[node] = component_id

    rows: list[dict[str, object]] = []
    for node, attrs in graph.nodes(data=True):
        row = {"username": node, "component_id": component_map[node]}
        row.update(attrs)
        rows.append(row)

    return pd.DataFrame(rows).sort_values(["component_id", "username"]).reset_index(drop=True)


def build_edge_table(graph: nx.Graph) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for source, target, attrs in graph.edges(data=True):
        row = {"source": source, "target": target}
        row.update(attrs)
        rows.append(row)

    return pd.DataFrame(rows).sort_values(["source", "target"]).reset_index(drop=True)


def compute_network_metrics(graph: nx.Graph, lcc: nx.Graph) -> dict[str, float | int]:
    degrees = dict(graph.degree())
    weighted_degrees = dict(graph.degree(weight="weight"))

    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "connected_components": nx.number_connected_components(graph),
        "largest_component_size": lcc.number_of_nodes(),
        "largest_component_share": round(lcc.number_of_nodes() / graph.number_of_nodes(), 4),
        "density": round(nx.density(graph), 4),
        "average_degree": round(sum(degrees.values()) / max(len(degrees), 1), 4),
        "average_weighted_degree": round(sum(weighted_degrees.values()) / max(len(weighted_degrees), 1), 4),
        "max_degree": int(max(degrees.values())),
        "average_clustering": round(nx.average_clustering(graph), 4),
        "diameter_lcc": int(nx.diameter(lcc)),
        "average_shortest_path_lcc": round(nx.average_shortest_path_length(lcc), 4),
    }


def build_degree_distribution(graph: nx.Graph) -> pd.DataFrame:
    degree_counter = Counter(dict(graph.degree()).values())
    rows = [{"degree": degree, "node_count": count} for degree, count in sorted(degree_counter.items())]
    return pd.DataFrame(rows)


def build_centrality_outputs(lcc: nx.Graph, node_table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    degree_centrality = nx.degree_centrality(lcc)
    betweenness = nx.betweenness_centrality(lcc, weight="distance")
    closeness = nx.closeness_centrality(lcc, distance="distance")
    eigenvector = nx.eigenvector_centrality(lcc, weight="weight", max_iter=500)
    pagerank = power_iteration_pagerank(lcc, weight_attr="weight")
    weighted_degree = dict(lcc.degree(weight="weight"))
    raw_degree = dict(lcc.degree())

    centrality_df = pd.DataFrame(
        {
            "username": list(lcc.nodes()),
            "degree": [raw_degree[node] for node in lcc.nodes()],
            "weighted_degree": [round(weighted_degree[node], 4) for node in lcc.nodes()],
            "degree_centrality": [round(degree_centrality[node], 6) for node in lcc.nodes()],
            "betweenness_centrality": [round(betweenness[node], 6) for node in lcc.nodes()],
            "closeness_centrality": [round(closeness[node], 6) for node in lcc.nodes()],
            "eigenvector_centrality": [round(eigenvector[node], 6) for node in lcc.nodes()],
            "pagerank": [round(pagerank[node], 6) for node in lcc.nodes()],
        }
    )

    centrality_df = centrality_df.merge(
        node_table[["username", "primary_category", "categories", "follower_segment", "followers", "avg_likes", "avg_comments"]],
        on="username",
        how="left",
    )

    measures = [
        ("Degree Centrality", "degree_centrality"),
        ("Betweenness Centrality", "betweenness_centrality"),
        ("Closeness Centrality", "closeness_centrality"),
        ("Eigenvector Centrality", "eigenvector_centrality"),
        ("PageRank", "pagerank"),
    ]

    top_rows: list[dict[str, object]] = []
    for measure_name, column_name in measures:
        subset = centrality_df.sort_values([column_name, "weighted_degree", "username"], ascending=[False, False, True]).head(5)
        for rank, (_, row) in enumerate(subset.iterrows(), start=1):
            top_rows.append(
                {
                    "measure": measure_name,
                    "rank": rank,
                    "username": row["username"],
                    "score": row[column_name],
                    "degree": int(row["degree"]),
                    "weighted_degree": row["weighted_degree"],
                    "categories": row["categories"],
                    "follower_segment": row["follower_segment"],
                }
            )

    top5_df = pd.DataFrame(top_rows)
    return centrality_df.sort_values("username").reset_index(drop=True), top5_df


def summarize_community_categories(community_nodes: list[str], node_table: pd.DataFrame) -> str:
    categories = Counter()
    category_lookup = node_table.set_index("username")["categories"].to_dict()
    for node in community_nodes:
        for category in split_field(category_lookup.get(node, "")):
            categories[category] += 1
    return ", ".join(f"{category} ({count})" for category, count in categories.most_common(5))


def build_community_outputs(
    lcc: nx.Graph,
    node_table: pd.DataFrame,
    centrality_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:
    communities = list(nx.community.louvain_communities(lcc, weight="weight", seed=RANDOM_SEED))
    modularity_score = nx.community.modularity(lcc, communities, weight="weight")

    node_to_community: dict[str, int] = {}
    for community_id, community_nodes in enumerate(sorted(communities, key=len, reverse=True), start=1):
        for node in community_nodes:
            node_to_community[node] = community_id

    assignments = pd.DataFrame(
        {
            "username": list(node_to_community.keys()),
            "community_id": [node_to_community[node] for node in node_to_community],
        }
    )

    community_rows: list[dict[str, object]] = []
    for community_id, community_nodes in enumerate(sorted(communities, key=len, reverse=True), start=1):
        community_node_list = sorted(community_nodes)
        community_rows.append(
            {
                "community_id": community_id,
                "size": len(community_node_list),
                "share_of_lcc": round(len(community_node_list) / lcc.number_of_nodes(), 4),
                "top_categories": summarize_community_categories(community_node_list, node_table),
                "sample_nodes": ", ".join(community_node_list[:8]),
            }
        )

    bridge_rows: list[dict[str, object]] = []
    betweenness_lookup = centrality_df.set_index("username")["betweenness_centrality"].to_dict()
    for node in lcc.nodes():
        own_community = node_to_community[node]
        external_neighbors = sum(1 for neighbor in lcc.neighbors(node) if node_to_community[neighbor] != own_community)
        if external_neighbors == 0:
            continue
        bridge_rows.append(
            {
                "username": node,
                "community_id": own_community,
                "external_neighbor_count": external_neighbors,
                "betweenness_centrality": betweenness_lookup[node],
            }
        )

    bridges_df = pd.DataFrame(bridge_rows).sort_values(
        ["external_neighbor_count", "betweenness_centrality", "username"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return (
        assignments.sort_values(["community_id", "username"]).reset_index(drop=True),
        pd.DataFrame(community_rows),
        bridges_df,
        round(modularity_score, 6),
    )


def summarize_graph_state(graph: nx.Graph) -> dict[str, float | int]:
    lcc = largest_connected_component(graph)
    degrees = dict(graph.degree())
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "components": nx.number_connected_components(graph),
        "largest_component_size": lcc.number_of_nodes(),
        "density": round(nx.density(graph), 4),
        "average_degree": round(sum(degrees.values()) / max(len(degrees), 1), 4),
        "diameter_lcc": int(nx.diameter(lcc)),
    }


def build_robustness_table(graph: nx.Graph, centrality_df: pd.DataFrame) -> pd.DataFrame:
    random.seed(RANDOM_SEED)
    rows: list[dict[str, object]] = []

    baseline = summarize_graph_state(graph)
    baseline["scenario"] = "Baseline"
    rows.append(baseline)

    highest_degree_node = centrality_df.sort_values(
        ["degree_centrality", "weighted_degree", "username"],
        ascending=[False, False, True],
    ).iloc[0]["username"]
    degree_removed = graph.copy()
    degree_removed.remove_node(highest_degree_node)
    result = summarize_graph_state(degree_removed)
    result["scenario"] = f"Highest degree node removed ({highest_degree_node})"
    rows.append(result)

    highest_betweenness_node = centrality_df.sort_values(
        ["betweenness_centrality", "weighted_degree", "username"],
        ascending=[False, False, True],
    ).iloc[0]["username"]
    betweenness_removed = graph.copy()
    betweenness_removed.remove_node(highest_betweenness_node)
    result = summarize_graph_state(betweenness_removed)
    result["scenario"] = f"Highest betweenness node removed ({highest_betweenness_node})"
    rows.append(result)

    top_20_betweenness = centrality_df.sort_values(
        ["betweenness_centrality", "weighted_degree", "username"],
        ascending=[False, False, True],
    ).head(20)["username"].tolist()
    targeted_removed = graph.copy()
    targeted_removed.remove_nodes_from(top_20_betweenness)
    result = summarize_graph_state(targeted_removed)
    result["scenario"] = "Top 20 betweenness nodes removed"
    rows.append(result)

    random_trials: list[dict[str, float | int]] = []
    node_list = list(graph.nodes())
    for _ in range(30):
        sampled_nodes = random.sample(node_list, 20)
        sampled_graph = graph.copy()
        sampled_graph.remove_nodes_from(sampled_nodes)
        random_trials.append(summarize_graph_state(sampled_graph))

    averaged_random = {
        "scenario": "Average of 30 random 20-node removals",
        "nodes": round(sum(item["nodes"] for item in random_trials) / len(random_trials), 4),
        "edges": round(sum(item["edges"] for item in random_trials) / len(random_trials), 4),
        "components": round(sum(item["components"] for item in random_trials) / len(random_trials), 4),
        "largest_component_size": round(sum(item["largest_component_size"] for item in random_trials) / len(random_trials), 4),
        "density": round(sum(item["density"] for item in random_trials) / len(random_trials), 4),
        "average_degree": round(sum(item["average_degree"] for item in random_trials) / len(random_trials), 4),
        "diameter_lcc": round(sum(item["diameter_lcc"] for item in random_trials) / len(random_trials), 4),
    }
    rows.append(averaged_random)

    return pd.DataFrame(rows)


def save_adjacency_matrix(graph: nx.Graph, destination: Path) -> None:
    adjacency = nx.to_pandas_adjacency(graph, dtype=float, weight="weight")
    adjacency.to_csv(destination)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    header = "| " + " | ".join(str(column) for column in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join([header, separator, *rows])


def top_category_legend(node_table: pd.DataFrame, limit: int = 10) -> list[str]:
    category_counts = node_table["primary_category"].value_counts()
    return category_counts.head(limit).index.tolist()


def component_dominant_categories(graph: nx.Graph, node_table: pd.DataFrame, limit: int = 2) -> list[tuple[list[str], list[str]]]:
    category_lookup = node_table.set_index("username")["primary_category"].to_dict()
    output: list[tuple[list[str], list[str]]] = []
    for component_nodes in sorted(nx.connected_components(graph), key=len, reverse=True):
        categories = [category_lookup.get(node, "unknown") for node in component_nodes]
        top_categories = [item[0] for item in Counter(categories).most_common(limit)]
        output.append((sorted(component_nodes), top_categories))
    return output


def build_component_layout(graph: nx.Graph) -> dict[str, tuple[float, float]]:
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    if not components:
        return {}

    packed_positions: dict[str, tuple[float, float]] = {}
    x_cursor = 0.0
    spacing = 2.8

    for index, component_nodes in enumerate(components):
        subgraph = graph.subgraph(component_nodes).copy()
        component_size = max(subgraph.number_of_nodes(), 1)
        local_k = max(0.22, min(0.55, 2.6 / math.sqrt(component_size)))
        local_positions = nx.spring_layout(
            subgraph,
            seed=RANDOM_SEED + index,
            weight="weight",
            k=local_k,
            iterations=350,
        )

        xs = [position[0] for position in local_positions.values()]
        ys = [position[1] for position in local_positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max(max_x - min_x, 1e-6)
        height = max(max_y - min_y, 1e-6)
        scale = max(1.0, math.sqrt(component_size) / 2.3)

        for node, (x_pos, y_pos) in local_positions.items():
            normalized_x = ((x_pos - min_x) / width - 0.5) * scale
            normalized_y = ((y_pos - min_y) / height - 0.5) * scale
            packed_positions[node] = (normalized_x + x_cursor, normalized_y)

        x_cursor += scale + spacing

    return packed_positions


def draw_network_overview(graph: nx.Graph, node_table: pd.DataFrame, destination: Path) -> dict[str, tuple[float, float]]:
    positions = build_component_layout(graph)
    categories = top_category_legend(node_table)
    color_map = plt.get_cmap("tab20", max(len(categories), 1))
    category_to_color = {category: color_map(index) for index, category in enumerate(categories)}
    default_color = (0.7, 0.7, 0.7, 0.8)

    node_colors = [
        category_to_color.get(graph.nodes[node].get("primary_category", "unknown"), default_color)
        for node in graph.nodes()
    ]

    weighted_degree_lookup = dict(graph.degree(weight="weight"))
    node_sizes = [28 + weighted_degree_lookup.get(node, 0.0) * 4.5 for node in graph.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(graph, positions, alpha=0.12, edge_color="#94a3b8", width=0.6)
    nx.draw_networkx_nodes(
        graph,
        positions,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=0.2,
        edgecolors="#374151",
    )
    top_nodes = sorted(weighted_degree_lookup, key=weighted_degree_lookup.get, reverse=True)[:12]
    labels = {node: node for node in top_nodes}
    nx.draw_networkx_labels(
        graph,
        positions,
        labels=labels,
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.72, "edgecolor": "none", "pad": 0.2},
    )

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label=category, markerfacecolor=category_to_color[category], markersize=8)
        for category in categories
    ]
    if legend_handles:
        plt.legend(
            handles=legend_handles,
            title="Baskin kategoriler",
            loc="upper left",
            bbox_to_anchor=(1.01, 1.0),
            frameon=False,
            fontsize=10,
            title_fontsize=11,
        )

    plt.title("Genel Ag Grafigi: Creator Benzerlik Omurgasi", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()

    return positions


def draw_network_overview_polished(
    graph: nx.Graph,
    node_table: pd.DataFrame,
    positions: dict[str, tuple[float, float]],
    destination: Path,
) -> None:
    categories = top_category_legend(node_table, limit=8)
    color_map = plt.get_cmap("Set2", max(len(categories), 1))
    category_to_color = {category: color_map(index) for index, category in enumerate(categories)}
    default_color = (0.78, 0.78, 0.78, 0.85)
    weighted_degree_lookup = dict(graph.degree(weight="weight"))
    node_colors = [
        category_to_color.get(graph.nodes[node].get("primary_category", "unknown"), default_color)
        for node in graph.nodes()
    ]
    node_sizes = [36 + weighted_degree_lookup.get(node, 0.0) * 5.2 for node in graph.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(graph, positions, alpha=0.13, edge_color="#cbd5e1", width=0.65)
    nx.draw_networkx_nodes(
        graph,
        positions,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=0.25,
        edgecolors="#334155",
    )

    top_nodes = sorted(weighted_degree_lookup, key=weighted_degree_lookup.get, reverse=True)[:10]
    nx.draw_networkx_labels(
        graph,
        positions,
        labels={node: node for node in top_nodes},
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none", "pad": 0.22},
    )

    component_labels = component_dominant_categories(graph, node_table)
    for index, (component_nodes, top_categories) in enumerate(component_labels, start=1):
        xs = [positions[node][0] for node in component_nodes]
        ys = [positions[node][1] for node in component_nodes]
        x_pos = sum(xs) / len(xs)
        y_pos = max(ys) + 0.65
        plt.text(
            x_pos,
            y_pos,
            f"Bilesen {index}: " + ", ".join(top_categories),
            fontsize=11,
            fontweight="bold",
            ha="center",
            va="bottom",
            bbox={"facecolor": "white", "alpha": 0.88, "edgecolor": "#cbd5e1", "boxstyle": "round,pad=0.25"},
        )

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label=category, markerfacecolor=category_to_color[category], markersize=9)
        for category in categories
    ]
    category_legend = plt.legend(
        handles=legend_handles,
        title="Baskin kategoriler",
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
    )
    plt.gca().add_artist(category_legend)
    size_handles = [
        plt.scatter([], [], s=size, color="#94a3b8", edgecolors="#334155")
        for size in (80, 180, 320)
    ]
    plt.legend(
        size_handles,
        ["Dusuk weighted degree", "Orta weighted degree", "Yuksek weighted degree"],
        title="Dugum boyutu",
        loc="upper left",
        bbox_to_anchor=(1.01, 0.72),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
        scatterpoints=1,
    )
    plt.title("Genel Ag Grafigi: Creator Benzerlik Omurgasi", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_centrality_graph(
    lcc: nx.Graph,
    centrality_df: pd.DataFrame,
    positions: dict[str, tuple[float, float]],
    destination: Path,
) -> None:
    local_positions = {node: positions[node] for node in lcc.nodes()}
    score_lookup = centrality_df.set_index("username")["betweenness_centrality"].to_dict()
    node_sizes = [500 + score_lookup[node] * 18000 for node in lcc.nodes()]
    node_colors = [score_lookup[node] for node in lcc.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(lcc, local_positions, alpha=0.12, edge_color="#94a3b8", width=0.6)
    nodes = nx.draw_networkx_nodes(
        lcc,
        local_positions,
        node_size=node_sizes,
        node_color=node_colors,
        cmap="YlOrRd",
        linewidths=0.3,
        edgecolors="#111827",
    )
    top_nodes = centrality_df.sort_values(
        ["betweenness_centrality", "weighted_degree", "username"],
        ascending=[False, False, True],
    ).head(12)["username"]
    labels = {node: node for node in top_nodes}
    nx.draw_networkx_labels(
        lcc,
        local_positions,
        labels=labels,
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.72, "edgecolor": "none", "pad": 0.2},
    )
    colorbar = plt.colorbar(nodes, shrink=0.78)
    colorbar.ax.tick_params(labelsize=10)
    plt.title("Merkezilik Grafigi: Betweenness Temelli Kopru Dugumler", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_centrality_graph_polished(
    lcc: nx.Graph,
    centrality_df: pd.DataFrame,
    positions: dict[str, tuple[float, float]],
    destination: Path,
) -> None:
    local_positions = {node: positions[node] for node in lcc.nodes()}
    score_lookup = centrality_df.set_index("username")["betweenness_centrality"].to_dict()
    weighted_lookup = centrality_df.set_index("username")["weighted_degree"].to_dict()
    node_sizes = [520 + score_lookup[node] * 19500 for node in lcc.nodes()]
    node_colors = [score_lookup[node] for node in lcc.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(lcc, local_positions, alpha=0.13, edge_color="#cbd5e1", width=0.65)
    nodes = nx.draw_networkx_nodes(
        lcc,
        local_positions,
        node_size=node_sizes,
        node_color=node_colors,
        cmap="YlOrRd",
        linewidths=0.35,
        edgecolors="#1f2937",
    )
    top_nodes = centrality_df.sort_values(
        ["betweenness_centrality", "weighted_degree", "username"],
        ascending=[False, False, True],
    ).head(8)["username"].tolist()
    secondary_nodes = centrality_df.sort_values(
        ["weighted_degree", "betweenness_centrality", "username"],
        ascending=[False, False, True],
    ).head(6)["username"].tolist()
    label_nodes = list(dict.fromkeys(top_nodes + secondary_nodes))
    nx.draw_networkx_labels(
        lcc,
        local_positions,
        labels={node: node for node in label_nodes},
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 0.22},
    )
    colorbar = plt.colorbar(nodes, shrink=0.78)
    colorbar.ax.tick_params(labelsize=10)
    colorbar.set_label("Betweenness centrality", fontsize=11)
    size_handles = [
        plt.scatter([], [], s=size, color="#fbbf24", edgecolors="#1f2937")
        for size in (700, 1400, 2400)
    ]
    plt.legend(
        size_handles,
        ["Dusuk kopru rolu", "Orta kopru rolu", "Yuksek kopru rolu"],
        title="Dugum boyutu",
        loc="upper left",
        bbox_to_anchor=(1.01, 0.78),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
        scatterpoints=1,
    )
    plt.title("Merkezilik Grafigi: Betweenness Temelli Kopru Dugumler", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_community_graph(
    lcc: nx.Graph,
    community_assignments: pd.DataFrame,
    bridges_df: pd.DataFrame,
    positions: dict[str, tuple[float, float]],
    destination: Path,
) -> None:
    local_positions = {node: positions[node] for node in lcc.nodes()}
    assignment_lookup = community_assignments.set_index("username")["community_id"].to_dict()
    communities = sorted(community_assignments["community_id"].unique())
    color_map = plt.get_cmap("tab20", max(len(communities), 1))
    node_colors = [color_map(communities.index(assignment_lookup[node])) for node in lcc.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(lcc, local_positions, alpha=0.10, edge_color="#9ca3af", width=0.6)
    nx.draw_networkx_nodes(lcc, local_positions, node_size=84, node_color=node_colors, linewidths=0.25, edgecolors="#ffffff")
    top_bridge_nodes = bridges_df.head(12)["username"].tolist()
    labels = {node: node for node in top_bridge_nodes}
    nx.draw_networkx_labels(
        lcc,
        local_positions,
        labels=labels,
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.72, "edgecolor": "none", "pad": 0.2},
    )
    plt.title("Topluluk Grafigi: Louvain Topluluk Yapisi", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_community_graph_polished(
    lcc: nx.Graph,
    community_assignments: pd.DataFrame,
    bridges_df: pd.DataFrame,
    positions: dict[str, tuple[float, float]],
    destination: Path,
) -> None:
    local_positions = {node: positions[node] for node in lcc.nodes()}
    assignment_lookup = community_assignments.set_index("username")["community_id"].to_dict()
    communities = sorted(community_assignments["community_id"].unique())
    color_map = plt.get_cmap("tab10", max(len(communities), 1))
    node_colors = [color_map(communities.index(assignment_lookup[node])) for node in lcc.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(lcc, local_positions, alpha=0.11, edge_color="#d1d5db", width=0.65)
    nx.draw_networkx_nodes(
        lcc,
        local_positions,
        node_size=92,
        node_color=node_colors,
        linewidths=0.25,
        edgecolors="#ffffff",
    )
    top_bridge_nodes = bridges_df.head(10)["username"].tolist()
    nx.draw_networkx_labels(
        lcc,
        local_positions,
        labels={node: node for node in top_bridge_nodes},
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none", "pad": 0.2},
    )
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label=f"Topluluk {community_id}", markerfacecolor=color_map(index), markersize=9)
        for index, community_id in enumerate(communities)
    ]
    community_legend = plt.legend(
        handles=legend_handles,
        title="Louvain topluluklari",
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
    )
    plt.gca().add_artist(community_legend)
    label_handle = plt.Line2D([0], [0], marker="s", color="w", label="Etiketli dugumler = kopru adaylari", markerfacecolor="#111827", markersize=8)
    plt.legend(
        handles=[label_handle],
        loc="upper left",
        bbox_to_anchor=(1.01, 0.72),
        frameon=False,
        fontsize=10,
    )
    plt.title("Topluluk Grafigi: Louvain Topluluk Yapisi", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_degree_distribution(graph: nx.Graph, destination: Path) -> None:
    degrees = list(dict(graph.degree()).values())
    plt.figure(figsize=(18, 10))
    bins = range(min(degrees), max(degrees) + 2)
    plt.hist(degrees, bins=bins, color="#2563eb", edgecolor="white", rwidth=0.92)
    plt.title("Derece Dagilimi", fontsize=22)
    plt.xlabel("Derece", fontsize=16)
    plt.ylabel("Dugum Sayisi", fontsize=16)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_degree_distribution_polished(graph: nx.Graph, destination: Path) -> None:
    degrees = list(dict(graph.degree()).values())
    mean_degree = float(np.mean(degrees))
    median_degree = float(np.median(degrees))
    plt.figure(figsize=(18, 10))
    bins = range(min(degrees), max(degrees) + 2)
    plt.hist(degrees, bins=bins, color="#2563eb", edgecolor="white", rwidth=0.9)
    plt.axvline(mean_degree, color="#dc2626", linewidth=2.4, linestyle="--")
    plt.axvline(median_degree, color="#059669", linewidth=2.4, linestyle="-.")
    plt.title("Derece Dagilimi", fontsize=22)
    plt.xlabel("Derece", fontsize=16)
    plt.ylabel("Dugum Sayisi", fontsize=16)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(axis="y", alpha=0.25)
    plt.legend(
        [f"Ortalama derece = {mean_degree:.2f}", f"Medyan derece = {median_degree:.2f}"],
        loc="upper right",
        frameon=False,
        fontsize=11,
    )
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_community_size_chart(community_summary: pd.DataFrame, destination: Path) -> None:
    summary = community_summary.sort_values("size", ascending=False).copy()
    labels = [f"T{community_id}" for community_id in summary["community_id"]]
    plt.figure(figsize=(16, 9))
    bars = plt.bar(labels, summary["size"], color=plt.get_cmap("tab10").colors[: len(summary)])
    plt.title("Topluluk Buyuklukleri", fontsize=22)
    plt.xlabel("Topluluk", fontsize=15)
    plt.ylabel("Dugum sayisi", fontsize=15)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(axis="y", alpha=0.2)
    for bar, category_text in zip(bars, summary["top_categories"]):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            category_text.split(",")[0],
            ha="center",
            va="bottom",
            fontsize=9,
            rotation=0,
        )
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_top_centrality_comparison(centrality_top5: pd.DataFrame, destination: Path) -> None:
    selected_measures = [
        "Degree Centrality",
        "Betweenness Centrality",
        "Closeness Centrality",
        "Eigenvector Centrality",
        "PageRank",
    ]
    summary = centrality_top5[centrality_top5["rank"] == 1].copy()
    summary = summary[summary["measure"].isin(selected_measures)].set_index("measure").loc[selected_measures].reset_index()
    plt.figure(figsize=(16, 9))
    bars = plt.bar(summary["measure"], summary["score"], color=["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c"])
    plt.title("Merkezilik Olcutlerine Gore En Ust Dugumler", fontsize=22)
    plt.ylabel("Skor", fontsize=15)
    plt.xticks(rotation=15, ha="right", fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(axis="y", alpha=0.2)
    for bar, username in zip(bars, summary["username"]):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            username,
            ha="center",
            va="bottom",
            fontsize=10,
            rotation=0,
        )
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_backbone_overview(
    graph: nx.Graph,
    node_table: pd.DataFrame,
    destination: Path,
    min_weight: float = 0.45,
) -> None:
    strong_edges = [(u, v, data) for u, v, data in graph.edges(data=True) if float(data.get("weight", 0.0)) >= min_weight]
    backbone = nx.Graph()
    backbone.add_nodes_from(graph.nodes(data=True))
    backbone.add_edges_from(strong_edges)
    backbone.remove_nodes_from(list(nx.isolates(backbone)))
    if backbone.number_of_nodes() == 0:
        return

    positions = build_component_layout(backbone)
    category_lookup = node_table.set_index("username")["primary_category"].to_dict()
    top_categories = top_category_legend(node_table, limit=8)
    color_map = plt.get_cmap("Set2", max(len(top_categories), 1))
    category_to_color = {category: color_map(index) for index, category in enumerate(top_categories)}
    node_colors = [
        category_to_color.get(category_lookup.get(node, "unknown"), (0.8, 0.8, 0.8, 0.9))
        for node in backbone.nodes()
    ]
    weighted_degree_lookup = dict(backbone.degree(weight="weight"))
    node_sizes = [60 + weighted_degree_lookup.get(node, 0.0) * 14 for node in backbone.nodes()]

    plt.figure(figsize=(22, 14))
    nx.draw_networkx_edges(backbone, positions, alpha=0.24, edge_color="#94a3b8", width=1.0)
    nx.draw_networkx_nodes(
        backbone,
        positions,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=0.35,
        edgecolors="#334155",
    )
    top_nodes = sorted(weighted_degree_lookup, key=weighted_degree_lookup.get, reverse=True)[:16]
    nx.draw_networkx_labels(
        backbone,
        positions,
        labels={node: node for node in top_nodes},
        font_size=10,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 0.2},
    )
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label=category, markerfacecolor=category_to_color[category], markersize=9)
        for category in top_categories
    ]
    plt.legend(
        handles=legend_handles,
        title="Baskin kategoriler",
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
    )
    plt.title("Guculu Baglantilarla Ag Omurgasi", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_centrality_focus_subgraph(
    graph: nx.Graph,
    centrality_df: pd.DataFrame,
    destination: Path,
    focus_size: int = 28,
) -> None:
    top_nodes = centrality_df.sort_values(
        ["betweenness_centrality", "weighted_degree", "username"],
        ascending=[False, False, True],
    ).head(focus_size)["username"].tolist()
    focus_graph = graph.subgraph(top_nodes).copy()
    if focus_graph.number_of_nodes() == 0:
        return

    positions = nx.spring_layout(focus_graph, seed=RANDOM_SEED, weight="weight", k=0.55, iterations=350)
    score_lookup = centrality_df.set_index("username")["betweenness_centrality"].to_dict()
    node_sizes = [700 + score_lookup.get(node, 0.0) * 26000 for node in focus_graph.nodes()]
    node_colors = [score_lookup.get(node, 0.0) for node in focus_graph.nodes()]

    plt.figure(figsize=(22, 14))
    edge_widths = [1.0 + float(data.get("weight", 0.0)) * 3.2 for _, _, data in focus_graph.edges(data=True)]
    nx.draw_networkx_edges(focus_graph, positions, alpha=0.28, edge_color="#94a3b8", width=edge_widths)
    nodes = nx.draw_networkx_nodes(
        focus_graph,
        positions,
        node_size=node_sizes,
        node_color=node_colors,
        cmap="YlOrRd",
        linewidths=0.45,
        edgecolors="#1f2937",
    )
    nx.draw_networkx_labels(
        focus_graph,
        positions,
        labels={node: node for node in focus_graph.nodes()},
        font_size=9,
        font_weight="bold",
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "none", "pad": 0.18},
    )
    colorbar = plt.colorbar(nodes, shrink=0.78)
    colorbar.ax.tick_params(labelsize=10)
    colorbar.set_label("Betweenness centrality", fontsize=11)
    plt.title("En Onemli Kopru Dugumlerin Alt Agi", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def draw_community_meta_graph(
    lcc: nx.Graph,
    community_assignments: pd.DataFrame,
    destination: Path,
) -> None:
    assignment_lookup = community_assignments.set_index("username")["community_id"].to_dict()
    meta_graph = nx.Graph()

    for community_id, group in community_assignments.groupby("community_id"):
        meta_graph.add_node(
            int(community_id),
            size=int(group.shape[0]),
        )

    edge_weights: dict[tuple[int, int], int] = {}
    for source, target in lcc.edges():
        source_community = int(assignment_lookup[source])
        target_community = int(assignment_lookup[target])
        if source_community == target_community:
            continue
        edge_key = tuple(sorted((source_community, target_community)))
        edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

    for (source_community, target_community), weight in edge_weights.items():
        meta_graph.add_edge(source_community, target_community, weight=weight)

    positions = nx.spring_layout(meta_graph, seed=RANDOM_SEED, weight="weight", k=1.4, iterations=300)
    node_sizes = [meta_graph.nodes[node]["size"] * 90 for node in meta_graph.nodes()]
    node_colors = list(plt.get_cmap("tab10").colors[: meta_graph.number_of_nodes()])
    edge_widths = [1.0 + data["weight"] / 18 for _, _, data in meta_graph.edges(data=True)]

    plt.figure(figsize=(16, 10))
    nx.draw_networkx_edges(meta_graph, positions, edge_color="#94a3b8", width=edge_widths, alpha=0.45)
    nx.draw_networkx_nodes(
        meta_graph,
        positions,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="#334155",
        linewidths=0.6,
    )
    labels = {
        node: f"Topluluk {node}\n({meta_graph.nodes[node]['size']} dugum)"
        for node in meta_graph.nodes()
    }
    nx.draw_networkx_labels(meta_graph, positions, labels=labels, font_size=10, font_weight="bold")
    plt.title("Topluluklar Arasi Meta-Ag", fontsize=22)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(destination, dpi=360, bbox_inches="tight")
    plt.close()


def interpret_density(density: float) -> str:
    if density >= 0.10:
        return "oldukca sik"
    if density >= 0.05:
        return "orta yogunlukta"
    return "gorece seyrek"


def interpret_diameter(diameter: int) -> str:
    if diameter <= 4:
        return "kompakt"
    if diameter <= 7:
        return "orta duzeyde kompakt"
    return "daginik"


def write_markdown_report(
    destination: Path,
    input_path: Path,
    metrics: dict[str, float | int],
    node_table: pd.DataFrame,
    edge_table: pd.DataFrame,
    centrality_top5: pd.DataFrame,
    community_summary: pd.DataFrame,
    bridges_df: pd.DataFrame,
    modularity_score: float,
    robustness_df: pd.DataFrame,
    figures_dir: Path,
) -> None:
    lcc_share = float(metrics["largest_component_share"]) * 100
    density_text = interpret_density(float(metrics["density"]))
    diameter_text = interpret_diameter(int(metrics["diameter_lcc"]))
    largest_community = community_summary.sort_values(["size", "community_id"], ascending=[False, True]).iloc[0]
    top_degree = centrality_top5[centrality_top5["measure"] == "Degree Centrality"].iloc[0]
    top_betweenness = centrality_top5[centrality_top5["measure"] == "Betweenness Centrality"].iloc[0]
    top_closeness = centrality_top5[centrality_top5["measure"] == "Closeness Centrality"].iloc[0]
    top_eigenvector = centrality_top5[centrality_top5["measure"] == "Eigenvector Centrality"].iloc[0]
    top_pagerank = centrality_top5[centrality_top5["measure"] == "PageRank"].iloc[0]
    top_bridge = bridges_df.iloc[0] if not bridges_df.empty else None
    baseline = robustness_df.iloc[0]
    targeted = robustness_df[robustness_df["scenario"] == "Top 20 betweenness nodes removed"].iloc[0]
    random_average = robustness_df[robustness_df["scenario"] == "Average of 30 random 20-node removals"].iloc[0]

    report = f"""# Sosyal Ag Analizi Proje Raporu

## 1. Proje Basligi ve Problem Tanimi

**Proje basligi:** Urun odakli influencer onerisi icin sosyal ag temelli creator omurgasi analizi

Bu projede analiz edilen ag, urun odakli influencer onerisi sisteminin karar omurgasi olarak kullanilan creator benzerlik agidir. Dugumler tekil creator hesaplarini temsil etmektedir. Kenarlar ise iki creator arasindaki kategori ve hashtag benzerligini gostermektedir. Ag **yonlusuz** ve **agirlikli** olarak modellenmistir. Kenar agirligi, kategori Jaccard benzerliginin %75'i ile hashtag Jaccard benzerliginin %25'inin toplamindan uretilmistir.

**Arastirma sorusu:** Bir urun sorgusu verildiginde sistem hangi influencer'i alan otoritesi, etkilesim ve gerekirse kopru rolu uzerinden one cikarmalidir; bunu destekleyen ag yapisi nasil gorunmektedir?

## 2. Veri Seti

Veri kaynagi proje kapsaminda Apify tabanli Instagram profil ve hashtag taramasi ile olusturulan yerel veri setidir. Analizde kullanilan temiz veri dosyasi:

- `{input_path}`

| Baslik | Aciklama |
|---|---|
| Veri kaynagi | Instagram profil/hashtag taramasi, yerel islenmis veri |
| Dugum turu | Creator / influencer hesabi |
| Kenar turu | Icerik benzerligi (kategori + hashtag overlap) |
| Dugum sayisi | {metrics["node_count"]} |
| Kenar sayisi | {metrics["edge_count"]} |
| Veri formati | CSV, GraphML, PNG, Markdown, Python |

## 3. Ag Modelleme

Ag su sekilde tanimlanmistir:

**G = (V, E)**

- **V:** creator hesaplari
- **E:** iki creator arasindaki benzerlik kenarlari

Beklenen ciktilar bu proje ile birlikte otomatik uretilmistir:

- Dugum listesi
- Kenar listesi
- Komsuluk matrisi
- GraphML formati
- Ag gorselleri

Projede kullanilan temel Python dosyalari:

- `sna_project.py`: agi kurar, olcutleri hesaplar, gorselleri, raporu ve notebook'u uretir.
- `recommender.py`: urun sorgusu geldikten sonra ag olcutlerini kullanarak influencer siralar.
- `taxonomy.py`: urun sinyallerini kategori ve kullanim baglamina donusturen sozluk ve yorumlama katmanini yonetir.
- `app.py`: sistemi basit bir web arayuzu uzerinden calistirir.

## 4. Temel Ag Olcutleri

| Olcut | Deger |
|---|---|
| Dugum sayisi | {metrics["node_count"]} |
| Kenar sayisi | {metrics["edge_count"]} |
| Bagli bilesen sayisi | {metrics["connected_components"]} |
| En buyuk bilesen | {metrics["largest_component_size"]} dugum ({lcc_share:.2f}%) |
| Yogunluk | {metrics["density"]} |
| Ortalama derece | {metrics["average_degree"]} |
| Ortalama agirlikli derece | {metrics["average_weighted_degree"]} |
| Ortalama kumeleme katsayisi | {metrics["average_clustering"]} |
| Cap (en buyuk bagli bilesen) | {metrics["diameter_lcc"]} |
| Ortalama en kisa yol (LCC) | {metrics["average_shortest_path_lcc"]} |

Bu sonuclar agin genel olarak **{density_text}** bir yapida oldugunu gostermektedir. Cap degeri {metrics["diameter_lcc"]} oldugu icin cekirdek yapinin **{diameter_text}** oldugu soylenebilir. Tum ag iki bagli bilesenden olusmaktadir; bu nedenle cap ve yakinlik temelli olcutler en buyuk bagli bilesen uzerinden yorumlanmistir.

## 5. Merkezilik Analizi

Merkezilik hesaplari en buyuk bagli bilesen uzerinden yapilmistir.

### Top 5 Degree Centrality
{dataframe_to_markdown(centrality_top5[centrality_top5["measure"] == "Degree Centrality"][["rank", "username", "score", "categories"]])}

### Top 5 Betweenness Centrality
{dataframe_to_markdown(centrality_top5[centrality_top5["measure"] == "Betweenness Centrality"][["rank", "username", "score", "categories"]])}

### Top 5 Closeness Centrality
{dataframe_to_markdown(centrality_top5[centrality_top5["measure"] == "Closeness Centrality"][["rank", "username", "score", "categories"]])}

### Top 5 Eigenvector Centrality
{dataframe_to_markdown(centrality_top5[centrality_top5["measure"] == "Eigenvector Centrality"][["rank", "username", "score", "categories"]])}

### Top 5 PageRank
{dataframe_to_markdown(centrality_top5[centrality_top5["measure"] == "PageRank"][["rank", "username", "score", "categories"]])}

Merkezilik sonuclari birlikte okundugunda:

- **En baglantili dugum:** `{top_degree["username"]}`. Bu hesap benzer ilgi alanlarina sahip cok sayida creator ile baglantilidir.
- **En guclu kopru dugum:** `{top_betweenness["username"]}`. Bu hesap farkli tema gruplari arasinda gecis noktasi gorevi gorur.
- **En hizli erisen dugum:** `{top_closeness["username"]}`. Bu hesap cekirdek ag icinde digerlerine daha kisa yollarla ulasabilmektedir.
- **Etkili dugum:** `{top_eigenvector["username"]}`. Bu hesap yalnizca cok baglantili degil, ayni zamanda onemli hesaplara da baglidir.
- **Otorite benzeri dugum:** `{top_pagerank["username"]}`. Bu dugum, agirlikli baglanti yapisi icinde yuksek genel oneme sahiptir.

## 6. Topluluk Analizi

Topluluk analizi Louvain algoritmasi ile yapilmistir.

| Olcut | Deger |
|---|---|
| Topluluk sayisi | {community_summary.shape[0]} |
| Modularity | {modularity_score} |
| En buyuk topluluk | Topluluk {int(largest_community["community_id"])} ({int(largest_community["size"])} dugum) |
| En buyuk toplulugun baskin temalari | {largest_community["top_categories"]} |

Topluluk ozet tablosu:

{dataframe_to_markdown(community_summary[["community_id", "size", "share_of_lcc", "top_categories"]])}

Topluluklar anlamsiz rastgele bolunmeler yerine kategori eksenlerine gore toparlanmistir. Bu durum modularity skorunun {modularity_score} olmasi ile de desteklenmektedir. {f'En belirgin topluluklar arasi kopru dugum `{top_bridge["username"]}` olarak gorunmektedir.' if top_bridge is not None else 'Topluluklar arasi kopru dugumler sinirli sayidadir.'}

## 7. Gorsellestirme

Olusturulan gorseller:

1. Genel ag grafigi: `{figures_dir / "01_network_overview.png"}`
2. Merkezilik degerlerine gore ag grafigi: `{figures_dir / "02_betweenness_centrality_network.png"}`
3. Topluluklara gore renklendirilmis ag grafigi: `{figures_dir / "03_louvain_communities.png"}`
4. Derece dagilimi: `{figures_dir / "04_degree_distribution.png"}`

## 8. Kisa Dayaniklilik Analizi

Dayaniklilik tablosu:

{dataframe_to_markdown(robustness_df)}

Tek bir en yuksek degree dugumunun cikmasi agi dramatik bicimde parcalamamistir. Buna karsin en yuksek betweenness dugumleri hedefli bicimde cikarildiginda cap degeri `{baseline["diameter_lcc"]}`'den `{targeted["diameter_lcc"]}`'e cikmistir. Rastgele 20 dugum cikarildiginda ortalama cap `{random_average["diameter_lcc"]}` seviyesinde kalmistir. Bu da agin bagli kalma acisindan dayanikli, fakat kopru dugumler kaybedildiginde ulasim verimliligi acisindan hassas oldugunu gostermektedir.

## 9. Sonuc

Bu agda creator hesaplari konu benzerligine gore belirgin alt topluluklar olusturmaktadir. Bu yapi, urun odakli influencer onerisi yapan sistemin omurgasini olusturur. En onemli dugumler tek bir olcekte degil, farkli merkezilik olcutlerinde farkli roller ustlenmektedir: bazi hesaplar alan otoritesi, bazi hesaplar ise topluluklar arasi koprudur. Ag yapisi yogun ve yuksek kumeleme katsayisina sahiptir; bu da benzer temalara sahip creatorlarin kendi iclerinde guclu kumeleme egilimi gosterdigini dusundurmektedir.

Bu nedenle proje yalnizca urun-kelime eslestirmesi yapan bir yapi degildir. Urun sorgusu once urun sinyallerine ayrilir, ardindan bu sinyaller creator graph uzerindeki merkezilik, topluluk ve kopru olculeri ile birlestirilerek son tavsiye uretilir.

Calismanin temel sinirliliklari sunlardir:

- Ag benzerlik temelli kuruldugu icin gercek takip/friend iliskilerini dogrudan temsil etmez.
- Hashtag verisi paylasimlardan turetildigi icin profilin tum icerik stratejisini tam yansitmayabilir.
- Veri seti belirli hashtag ve profil taramalarina dayanmaktadir; tum Instagram ekosistemini kapsamaz.
"""

    destination.write_text(report, encoding="utf-8")


def write_notebook(notebook_path: Path) -> None:
    root_line = "PROJECT_ROOT = Path.cwd() if (Path.cwd() / 'sna_project.py').exists() else Path.cwd().parent"
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Sosyal Ag Analizi Projesi\n",
                "\n",
                "Bu notebook, urun odakli influencer onerisi yapan sistemin creator benzerlik agini analiz etmek icin hazirlanmistir.\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Problem Tanimi\n",
                "\n",
                "Amac, urun girdisi verildiginde hangi hesaplarin alan otoritesi veya kopru roluyle one ciktigini ve bu kararin arkasindaki ag yapisini incelemektir.\n",
                "Bu nedenle notebook yalnizca sayisal ag metriklerini degil, bu metriklerin influencer onerisi kararina nasil destek oldugunu da gostermektedir.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\n",
                "import pandas as pd\n",
                "from IPython.display import Image, display\n",
                "\n",
                f"{root_line}\n",
                "OUTPUT_DIR = PROJECT_ROOT / 'docs' / 'sna_project_outputs'\n",
                "TABLES_DIR = OUTPUT_DIR / 'tables'\n",
                "FIGURES_DIR = OUTPUT_DIR / 'figures'\n",
                "REPORT_PATH = PROJECT_ROOT / 'docs' / 'sna_project_report.md'\n",
                "\n",
                "print('Project root:', PROJECT_ROOT)\n",
                "print('Output dir:', OUTPUT_DIR)\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from sna_project import run_analysis\n",
                "\n",
                "result = run_analysis()\n",
                "result['metrics']\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Veri Seti Ozeti\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "node_df = pd.read_csv(TABLES_DIR / 'node_list.csv')\n",
                "edge_df = pd.read_csv(TABLES_DIR / 'edge_list.csv')\n",
                "node_df.head(), edge_df.head()\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Temel Ag Olcutleri\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "metrics_df = pd.read_json(TABLES_DIR / 'network_metrics.json', typ='series')\n",
                "metrics_df\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Merkezilik Analizi\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "centrality_top5 = pd.read_csv(TABLES_DIR / 'centrality_top5.csv')\n",
                "centrality_top5\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Topluluk Analizi\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "community_summary = pd.read_csv(TABLES_DIR / 'community_summary.csv')\n",
                "community_summary\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Gorseller\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display(Image(filename=str(FIGURES_DIR / '01_network_overview.png')))\n",
                "display(Image(filename=str(FIGURES_DIR / '02_betweenness_centrality_network.png')))\n",
                "display(Image(filename=str(FIGURES_DIR / '03_louvain_communities.png')))\n",
                "display(Image(filename=str(FIGURES_DIR / '04_degree_distribution.png')))\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Dayaniklilik Analizi\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "robustness_df = pd.read_csv(TABLES_DIR / 'robustness_summary.csv')\n",
                "robustness_df\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Rapor\n",
                "\n",
                "Ayrintili yorum taslagi `docs/sna_project_report.md` dosyasina yazdirilmistir.\n",
            ],
        },
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.x",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")


def run_analysis(
    input_path: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    notebook_path: Path = DEFAULT_NOTEBOOK,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    records = load_creator_records(input_path)
    graph = build_creator_graph(records)
    lcc = largest_connected_component(graph)

    node_table = build_node_table(graph)
    edge_table = build_edge_table(graph)
    metrics = compute_network_metrics(graph, lcc)
    degree_distribution = build_degree_distribution(graph)
    centrality_df, centrality_top5 = build_centrality_outputs(lcc, node_table)
    community_assignments, community_summary, bridges_df, modularity_score = build_community_outputs(
        lcc,
        node_table,
        centrality_df,
    )
    robustness_df = build_robustness_table(graph, centrality_df)

    node_table.to_csv(tables_dir / "node_list.csv", index=False)
    edge_table.to_csv(tables_dir / "edge_list.csv", index=False)
    centrality_df.to_csv(tables_dir / "centrality_scores.csv", index=False)
    centrality_top5.to_csv(tables_dir / "centrality_top5.csv", index=False)
    community_assignments.to_csv(tables_dir / "community_assignments.csv", index=False)
    community_summary.to_csv(tables_dir / "community_summary.csv", index=False)
    bridges_df.to_csv(tables_dir / "bridge_nodes.csv", index=False)
    degree_distribution.to_csv(tables_dir / "degree_distribution.csv", index=False)
    robustness_df.to_csv(tables_dir / "robustness_summary.csv", index=False)
    (tables_dir / "network_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    save_adjacency_matrix(graph, tables_dir / "adjacency_matrix.csv")
    nx.write_adjlist(graph, tables_dir / "adjacency_list.txt")
    nx.write_graphml(graph, output_dir / "creator_similarity_graph.graphml")

    positions = draw_network_overview(graph, node_table, figures_dir / "01_network_overview.png")
    draw_centrality_graph(lcc, centrality_df, positions, figures_dir / "02_betweenness_centrality_network.png")
    draw_community_graph(lcc, community_assignments, bridges_df, positions, figures_dir / "03_louvain_communities.png")
    draw_degree_distribution(graph, figures_dir / "04_degree_distribution.png")
    draw_network_overview_polished(graph, node_table, positions, figures_dir / "05_network_overview_polished.png")
    draw_centrality_graph_polished(lcc, centrality_df, positions, figures_dir / "06_betweenness_centrality_network_polished.png")
    draw_community_graph_polished(lcc, community_assignments, bridges_df, positions, figures_dir / "07_louvain_communities_polished.png")
    draw_degree_distribution_polished(graph, figures_dir / "08_degree_distribution_polished.png")
    draw_community_size_chart(community_summary, figures_dir / "09_community_size_chart.png")
    draw_top_centrality_comparison(centrality_top5, figures_dir / "10_top_centrality_comparison.png")
    draw_backbone_overview(graph, node_table, figures_dir / "11_backbone_overview.png")
    draw_centrality_focus_subgraph(lcc, centrality_df, figures_dir / "12_centrality_focus_subgraph.png")
    draw_community_meta_graph(lcc, community_assignments, figures_dir / "13_community_meta_graph.png")

    report_path = BASE_DIR / "docs" / "sna_project_report.md"
    write_markdown_report(
        destination=report_path,
        input_path=input_path,
        metrics=metrics,
        node_table=node_table,
        edge_table=edge_table,
        centrality_top5=centrality_top5,
        community_summary=community_summary,
        bridges_df=bridges_df,
        modularity_score=modularity_score,
        robustness_df=robustness_df,
        figures_dir=figures_dir,
    )

    write_notebook(notebook_path)

    return {
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "report_path": str(report_path),
        "notebook_path": str(notebook_path),
        "metrics": metrics,
        "modularity": modularity_score,
        "largest_community_size": int(community_summary["size"].max()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a social network analysis project from the creator dataset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input CSV file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for tables and figures")
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK, help="Notebook destination")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_analysis(input_path=args.input, output_dir=args.output_dir, notebook_path=args.notebook)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
