from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recommender import recommend_influencers_from_dataset

FIGURE_DIR = ROOT / "docs" / "sna_project_outputs" / "figures"
OUTPUT_DIR = ROOT / "docs" / "sna_project_outputs"
TABLE_DIR = ROOT / "docs" / "sna_project_outputs" / "tables"
DATASET_PATH = ROOT / "data" / "processed" / "clean_creator_dataset.csv"


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 180,
            "savefig.dpi": 220,
            "font.size": 12,
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 10,
        }
    )


def draw_robustness_comparison() -> Path:
    robustness = pd.read_csv(TABLE_DIR / "robustness_summary.csv")

    scenarios = robustness["scenario"].tolist()
    largest_component = robustness["largest_component_size"].tolist()
    diameters = robustness["diameter_lcc"].tolist()

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), constrained_layout=True)
    colors = ["#1d3557", "#457b9d", "#e76f51", "#d62828", "#6c757d"]

    axes[0].barh(scenarios, largest_component, color=colors, edgecolor="#0b132b")
    axes[0].invert_yaxis()
    axes[0].set_title("Largest Connected Component")
    axes[0].set_xlabel("Node count")
    axes[0].grid(axis="x", linestyle="--", alpha=0.25)
    for index, value in enumerate(largest_component):
        axes[0].text(value + 2, index, f"{int(round(value))}", va="center", fontsize=10)

    axes[1].barh(scenarios, diameters, color=colors, edgecolor="#0b132b")
    axes[1].invert_yaxis()
    axes[1].set_title("Diameter Under Removal Scenarios")
    axes[1].set_xlabel("Diameter")
    axes[1].grid(axis="x", linestyle="--", alpha=0.25)
    for index, value in enumerate(diameters):
        axes[1].text(value + 0.04, index, f"{value:.2f}", va="center", fontsize=10)

    fig.suptitle("Robustness Comparison: Random vs Targeted Node Removal", fontsize=20, fontweight="bold")
    output_path = FIGURE_DIR / "14_robustness_comparison.png"
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def draw_recommendation_examples() -> Path:
    example_queries = [
        "kadin yuz serumu",
        "pipetli bardak",
        "anne bebek ve cilt bakim urunu",
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 7), constrained_layout=True)
    palette = ["#bc4749", "#3a86ff", "#6a994e", "#ff9f1c", "#6d597a"]

    for axis, query in zip(axes, example_queries):
        payload = recommend_influencers_from_dataset(
            product_query=query,
            top_k=5,
            dataset_path=DATASET_PATH,
        )
        recommendations = payload["recommendations"]
        labels = [item["username"] for item in recommendations][::-1]
        scores = [item["score"] for item in recommendations][::-1]
        mode = payload["intent"]["mode"]
        categories = ", ".join(payload["intent"]["matched_categories"])

        axis.barh(labels, scores, color=palette[: len(scores)], edgecolor="#22223b")
        axis.set_title(f"{query.title()}\nmode={mode} | kategoriler={categories}", fontsize=12, pad=12)
        axis.set_xlabel("Recommendation score")
        axis.grid(axis="x", linestyle="--", alpha=0.25)
        for y_pos, score in enumerate(scores):
            axis.text(score + 0.005, y_pos, f"{score:.3f}", va="center", fontsize=9)

    fig.suptitle("Sample Product Queries and Recommended Influencers", fontsize=20, fontweight="bold")
    output_path = FIGURE_DIR / "15_recommendation_examples.png"
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def draw_bridge_focus_compact() -> Path:
    graph = nx.read_graphml(OUTPUT_DIR / "creator_similarity_graph.graphml")
    centrality = pd.read_csv(TABLE_DIR / "centrality_scores.csv")
    top_bridge = centrality.sort_values("betweenness_centrality", ascending=False).head(15)
    focus_nodes = set(top_bridge["username"].tolist())

    for username in list(focus_nodes):
        if username in graph:
            focus_nodes.update(graph.neighbors(username))

    subgraph = graph.subgraph(focus_nodes).copy()
    if nx.number_connected_components(subgraph) > 1:
        largest_nodes = max(nx.connected_components(subgraph), key=len)
        subgraph = subgraph.subgraph(largest_nodes).copy()

    betweenness_map = (
        centrality.set_index("username")["betweenness_centrality"].to_dict()
    )
    node_sizes = [420 + betweenness_map.get(node, 0.0) * 14000 for node in subgraph.nodes()]
    node_colors = [betweenness_map.get(node, 0.0) for node in subgraph.nodes()]

    fig, ax = plt.subplots(figsize=(14, 9))
    pos = nx.spring_layout(subgraph, seed=42, k=0.62, iterations=250)

    nx.draw_networkx_edges(subgraph, pos, ax=ax, edge_color="#b0bec5", width=1.6, alpha=0.55)
    nodes = nx.draw_networkx_nodes(
        subgraph,
        pos,
        ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        cmap="YlOrRd",
        edgecolors="#263238",
        linewidths=0.8,
    )
    candidate_labels = (
        centrality[centrality["username"].isin(subgraph.nodes())]
        .sort_values("betweenness_centrality", ascending=False)
        .head(22)
    )
    selected_labels: dict[str, tuple[float, float]] = {}
    minimum_distance = 0.11

    for username in candidate_labels["username"]:
        if username not in pos:
            continue
        x_pos, y_pos = pos[username]
        if all(((x_pos - ox) ** 2 + (y_pos - oy) ** 2) ** 0.5 >= minimum_distance for ox, oy in selected_labels.values()):
            selected_labels[username] = (x_pos, y_pos)

    nx.draw_networkx_labels(
        subgraph,
        {node: coordinates for node, coordinates in selected_labels.items()},
        labels={node: node for node in selected_labels},
        ax=ax,
        font_size=8.5,
        font_weight="bold",
    )

    colorbar = fig.colorbar(nodes, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Betweenness centrality")
    ax.set_title("Compact Bridge-Node Focus Subgraph", fontsize=20, fontweight="bold", pad=16)
    ax.text(
        0.5,
        -0.06,
        "Only the non-overlapping highest-betweenness nodes are labeled; node size and color both increase with bridge importance.",
        ha="center",
        va="top",
        transform=ax.transAxes,
        fontsize=10,
    )
    ax.axis("off")
    output_path = FIGURE_DIR / "16_bridge_focus_compact.png"
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def draw_network_overview_presentation() -> Path:
    source = plt.imread(FIGURE_DIR / "05_network_overview_polished.png")
    fig = plt.figure(figsize=(16, 10), facecolor="white", constrained_layout=True)
    grid = fig.add_gridspec(1, 2, width_ratios=[2.35, 1.0])
    ax_image = fig.add_subplot(grid[0, 0])
    ax_text = fig.add_subplot(grid[0, 1])

    ax_image.imshow(source)
    ax_image.axis("off")

    ax_text.axis("off")
    ax_text.text(0.0, 0.95, "Bu Grafik Ne Anlatiyor?", fontsize=20, fontweight="bold", color="#1d3557", va="top")
    bullets = [
        "Renkler: her dugumun baskin kategori ailesini gosterir.",
        "Dugum buyuklugu: weighted degree arttikca buyur; yani daha cok ve daha guclu baglantiyi temsil eder.",
        "Soldaki buyuk yapi: creator graph'in ana cekirdek bilesenidir.",
        "Sagdaki kucuk ada: daha sinirli ve daha genel bir alt bileseni temsil eder.",
        "Bu yapi, influencerlarin rastgele degil, benzer ilgi alanlarina gore baglandigini gosterir.",
    ]
    y_pos = 0.84
    for bullet in bullets:
        ax_text.text(0.02, y_pos, f"- {bullet}", fontsize=13, color="#2b2d42", va="top", wrap=True)
        y_pos -= 0.14

    ax_text.text(
        0.0,
        0.12,
        "Bizim projede bu grafik, influencer seciminin tek tek hesaplara bakarak degil; creatorlar arasi yapiyi okuyarak yapildigini anlatir.",
        fontsize=12.5,
        color="#495057",
        va="top",
        wrap=True,
    )

    fig.suptitle("Genel Ag Grafigi: Creator Benzerlik Omurgasi", fontsize=24, fontweight="bold", color="#0b132b")
    output_path = FIGURE_DIR / "17_network_overview_presentation.png"
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def draw_degree_distribution_presentation() -> Path:
    source = plt.imread(FIGURE_DIR / "08_degree_distribution_polished.png")
    fig = plt.figure(figsize=(16, 10), facecolor="white", constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[3.2, 1.15])
    ax_image = fig.add_subplot(grid[0, 0])
    ax_text = fig.add_subplot(grid[1, 0])

    ax_image.imshow(source)
    ax_image.axis("off")

    ax_text.axis("off")
    ax_text.text(0.0, 0.90, "Bu Grafik Ne Anlatiyor?", fontsize=20, fontweight="bold", color="#1d3557", va="top")
    bullets = [
        "X ekseni dereceyi, Y ekseni bu dereceye sahip dugum sayisini gosterir.",
        "Sag kuyruk yapisi, agda hub niteliginde creatorlar oldugunu gosterir.",
        "Ortalama derece 34.50, medyan derece 38.00 civarindadir; yani cekirdek creatorlar gorece yogun baglantilara sahiptir.",
        "Bu bulgu, authority modunda neden bazi hesaplarin daha guclu aday haline geldigini destekler.",
    ]
    y_pos = 0.68
    for bullet in bullets:
        ax_text.text(0.02, y_pos, f"- {bullet}", fontsize=13, color="#2b2d42", va="top", wrap=True)
        y_pos -= 0.19

    fig.suptitle("Derece Dagilimi ve Hub Dugumler", fontsize=24, fontweight="bold", color="#0b132b")
    output_path = FIGURE_DIR / "18_degree_distribution_presentation.png"
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    _configure_matplotlib()
    generated = [
        draw_robustness_comparison(),
        draw_recommendation_examples(),
        draw_bridge_focus_compact(),
        draw_network_overview_presentation(),
        draw_degree_distribution_presentation(),
    ]
    for path in generated:
        print(path)


if __name__ == "__main__":
    main()
