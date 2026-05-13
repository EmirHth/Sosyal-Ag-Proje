from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path

import networkx as nx
import pandas as pd

from apify_scraper import summarize_scrape
from config import PROCESSED_DIR
from taxonomy import (
    ProductIntent,
    classify_follower_segment,
    expand_category_keywords,
    infer_product_intent,
    normalize_text,
)


DEFAULT_CREATOR_DATASET = PROCESSED_DIR / "clean_creator_dataset.csv"
SIMILARITY_THRESHOLD = 0.30


def _safe_log10(value: float | int | None) -> float:
    if not value or value <= 0:
        return 0.0
    return math.log10(float(value) + 1.0)


def _safe_float(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def _split_csv_field(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [item.strip() for item in str(value).split(",") if item and item.strip() and item.strip().lower() != "nan"]


def _jaccard_similarity(left: list[str] | tuple[str, ...], right: list[str] | tuple[str, ...]) -> float:
    left_set = {normalize_text(str(item)) for item in left if str(item).strip()}
    right_set = {normalize_text(str(item)) for item in right if str(item).strip()}
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _tag_score(top_hashtags: list[tuple[str, int]] | list[list], product_terms: list[str]) -> tuple[float, list[str]]:
    matches: list[str] = []
    score = 0.0
    normalized_terms = set(product_terms)

    for tag, count in top_hashtags or []:
        normalized_tag = normalize_text(str(tag).lstrip("#"))
        for term in normalized_terms:
            if term and (term in normalized_tag or normalized_tag in term):
                score += float(count)
                matches.append(str(tag))
                break

    return score, sorted(set(matches))


def _tag_score_from_strings(top_hashtags: list[str], product_terms: list[str]) -> tuple[int, list[str]]:
    matches: list[str] = []
    normalized_terms = set(product_terms)

    for tag in top_hashtags or []:
        normalized_tag = normalize_text(str(tag).lstrip("#"))
        for term in normalized_terms:
            if term and (term in normalized_tag or normalized_tag in term):
                matches.append(str(tag))
                break

    return len(set(matches)), sorted(set(matches))


def _category_overlap(user_categories: list[str], target_categories: list[str]) -> float:
    if not user_categories or not target_categories:
        return 0.0
    user_set = {normalize_text(item) for item in user_categories}
    target_set = {normalize_text(item) for item in target_categories}
    if "genel" in target_set:
        return 0.15
    overlap = user_set & target_set
    return len(overlap) / max(len(target_set), 1)


def _category_fit(user_categories: list[str], target_categories: list[str]) -> dict[str, float]:
    user_set = {normalize_text(item) for item in user_categories if normalize_text(item) != "genel"}
    target_set = {normalize_text(item) for item in target_categories if normalize_text(item) != "genel"}

    if not user_set or not target_set:
        return {
            "overlap_count": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    overlap = user_set & target_set
    precision = len(overlap) / max(len(user_set), 1)
    recall = len(overlap) / max(len(target_set), 1)
    f1 = 0.0 if precision + recall == 0 else (2 * precision * recall) / (precision + recall)
    return {
        "overlap_count": float(len(overlap)),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _engagement_rate(avg_likes: float, avg_comments: float, followers: float) -> float:
    if not followers or followers <= 0:
        return 0.0
    return (avg_likes + avg_comments * 3.0) / followers


def _normalize_metric_map(metric_map: dict[str, float]) -> dict[str, float]:
    if not metric_map:
        return {}
    values = list(metric_map.values())
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        return {key: 0.0 for key in metric_map}
    return {
        key: (value - min_value) / (max_value - min_value)
        for key, value in metric_map.items()
    }


def _power_iteration_pagerank(
    graph: nx.Graph,
    alpha: float = 0.85,
    weight_attr: str = "weight",
    max_iter: int = 500,
    tol: float = 1e-9,
) -> dict[str, float]:
    nodes = list(graph.nodes())
    if not nodes:
        return {}

    node_count = len(nodes)
    node_index = {node: index for index, node in enumerate(nodes)}
    matrix = [[0.0 for _ in nodes] for _ in nodes]

    for node in nodes:
        column_index = node_index[node]
        neighbors = list(graph.neighbors(node))
        if not neighbors:
            for row in range(node_count):
                matrix[row][column_index] = 1.0 / node_count
            continue

        weights = [float(graph[node][neighbor].get(weight_attr, 1.0)) for neighbor in neighbors]
        total = sum(weights)
        if total <= 0:
            for row in range(node_count):
                matrix[row][column_index] = 1.0 / node_count
            continue

        for neighbor, weight in zip(neighbors, weights):
            matrix[node_index[neighbor]][column_index] = weight / total

    scores = [1.0 / node_count for _ in nodes]
    teleport = [1.0 / node_count for _ in nodes]

    for _ in range(max_iter):
        next_scores = []
        for row in range(node_count):
            dot_product = sum(matrix[row][col] * scores[col] for col in range(node_count))
            next_scores.append(alpha * dot_product + (1.0 - alpha) * teleport[row])

        delta = sum(abs(left - right) for left, right in zip(next_scores, scores))
        scores = next_scores
        if delta < tol:
            break

    return {node: float(scores[node_index[node]]) for node in nodes}


def build_influencer_graph(summary: dict, product_query: str) -> tuple[nx.Graph, ProductIntent]:
    intent = infer_product_intent(product_query)
    product_terms = expand_category_keywords(intent.matched_categories)
    graph = nx.Graph()

    product_node = f"product::{intent.normalized_query}"
    graph.add_node(
        product_node,
        type="product",
        label=intent.query,
        categories=intent.matched_categories,
        keywords=product_terms,
    )

    for user in summary.get("users", []):
        username = user["username"]
        influencer_node = f"influencer::{username}"
        tag_score, matched_tags = _tag_score(user.get("top_hashtags", []), product_terms)
        engagement_score = _safe_log10(user.get("avg_likes", 0) + user.get("avg_comments", 0))
        follower_score = _safe_log10(user.get("followers", 0))
        category_score = _category_overlap(user.get("categories", []), intent.matched_categories)
        total_score = round(tag_score * 0.55 + engagement_score * 0.25 + follower_score * 0.10 + category_score * 5.0, 4)

        graph.add_node(
            influencer_node,
            type="influencer",
            username=username,
            followers=user.get("followers", 0),
            follower_segment=classify_follower_segment(user.get("followers")),
            avg_likes=round(user.get("avg_likes", 0), 2),
            avg_comments=round(user.get("avg_comments", 0), 2),
            categories=user.get("categories", []),
            top_hashtags=user.get("top_hashtags", []),
        )
        graph.add_edge(
            product_node,
            influencer_node,
            weight=total_score,
            tag_score=round(tag_score, 4),
            engagement_score=round(engagement_score, 4),
            follower_score=round(follower_score, 4),
            category_score=round(category_score, 4),
            matched_tags=matched_tags,
        )

    return graph, intent


def recommend_influencers(
    summary_path: str,
    product_query: str,
    top_k: int = 5,
    min_posts: int = 3,
    follower_segments: list[str] | None = None,
) -> dict:
    summary = summarize_scrape(summary_path)
    graph, intent = build_influencer_graph(summary, product_query)
    product_node = f"product::{intent.normalized_query}"

    ranked: list[dict] = []
    for neighbor in graph.neighbors(product_node):
        edge = graph.edges[product_node, neighbor]
        node = graph.nodes[neighbor]
        user_summary = next((user for user in summary.get("users", []) if user["username"] == node["username"]), None)
        if not user_summary or user_summary.get("posts", 0) < min_posts:
            continue
        if follower_segments and node.get("follower_segment") not in set(follower_segments):
            continue

        ranked.append(
            {
                "username": node["username"],
                "score": edge["weight"],
                "followers": node["followers"],
                "follower_segment": node["follower_segment"],
                "avg_likes": node["avg_likes"],
                "avg_comments": node["avg_comments"],
                "posts_analyzed": user_summary.get("posts", 0),
                "categories": node["categories"],
                "matched_tags": edge["matched_tags"],
                "score_breakdown": {
                    "tag_score": edge["tag_score"],
                    "engagement_score": edge["engagement_score"],
                    "follower_score": edge["follower_score"],
                    "category_score": edge["category_score"],
                },
                "reason": _build_reason(node, edge, intent),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {
        "product_query": product_query,
        "intent": {
            "matched_categories": intent.matched_categories,
            "matched_keywords": intent.matched_keywords,
        },
        "recommendations": ranked[:top_k],
        "graph": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        },
    }


def _build_reason(node: dict, edge: dict, intent: ProductIntent) -> str:
    matched_tags = ", ".join(f"#{tag}" for tag in edge.get("matched_tags", [])[:5]) or "dogrudan eslesen etiket bulunamadi"
    categories = ", ".join(node.get("categories", [])[:3]) or "kategori yok"
    return (
        f"{intent.query} icin {categories} ekseninde uygun gorunuyor. "
        f"Takipci segmenti: {node.get('follower_segment', 'unknown')}. "
        f"Eslesen etiketler: {matched_tags}. "
        f"Ortalama etkilesim {node.get('avg_likes', 0):.0f} begeni ve {node.get('avg_comments', 0):.0f} yorum."
    )


@lru_cache(maxsize=4)
def _prepare_creator_recommender_data(dataset_path: str) -> dict:
    df = pd.read_csv(dataset_path)

    records: list[dict] = []
    creator_graph = nx.Graph()

    for row in df.to_dict(orient="records"):
        username = str(row.get("username", "")).strip()
        if not username:
            continue

        categories = _split_csv_field(row.get("categories"))
        hashtags = _split_csv_field(row.get("top_hashtags"))
        followers = _safe_float(row.get("followers"))
        avg_likes = _safe_float(row.get("avg_likes"))
        avg_comments = _safe_float(row.get("avg_comments"))
        engagement_rate = _engagement_rate(avg_likes, avg_comments, followers)

        record = {
            "username": username,
            "posts": int(_safe_float(row.get("posts"))),
            "followers": followers,
            "follower_segment": str(row.get("follower_segment", classify_follower_segment(int(followers) if followers else 0))).strip() or "unknown",
            "avg_likes": round(avg_likes, 2),
            "avg_comments": round(avg_comments, 2),
            "categories": categories,
            "top_hashtags": hashtags,
            "primary_category": categories[0] if categories else "genel",
            "engagement_rate": engagement_rate,
        }
        records.append(record)
        creator_graph.add_node(
            username,
            categories=categories,
            primary_category=record["primary_category"],
            followers=followers,
            avg_likes=avg_likes,
            avg_comments=avg_comments,
        )

    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            category_similarity = _jaccard_similarity(left["categories"], right["categories"])
            hashtag_similarity = _jaccard_similarity(left["top_hashtags"], right["top_hashtags"])
            weight = category_similarity * 0.75 + hashtag_similarity * 0.25
            if weight < SIMILARITY_THRESHOLD:
                continue
            creator_graph.add_edge(
                left["username"],
                right["username"],
                weight=round(weight, 4),
                distance=round(1.0 / (weight + 1e-6), 6),
            )

    weighted_degree = {node: float(value) for node, value in creator_graph.degree(weight="weight")}
    pagerank = _power_iteration_pagerank(creator_graph, weight_attr="weight")
    betweenness = nx.betweenness_centrality(creator_graph, weight="distance")
    log_engagement = {
        record["username"]: _safe_log10(record["avg_likes"] + record["avg_comments"])
        for record in records
    }
    engagement_rate_map = {record["username"]: float(record["engagement_rate"]) for record in records}
    follower_log_map = {record["username"]: _safe_log10(record["followers"]) for record in records}

    norm_weighted_degree = _normalize_metric_map(weighted_degree)
    norm_pagerank = _normalize_metric_map({key: float(value) for key, value in pagerank.items()})
    norm_betweenness = _normalize_metric_map({key: float(value) for key, value in betweenness.items()})
    norm_log_engagement = _normalize_metric_map(log_engagement)
    norm_engagement_rate = _normalize_metric_map(engagement_rate_map)
    norm_follower_log = _normalize_metric_map(follower_log_map)

    feature_map: dict[str, dict[str, float]] = {}
    for record in records:
        username = record["username"]
        authority_score = 0.6 * norm_pagerank.get(username, 0.0) + 0.4 * norm_weighted_degree.get(username, 0.0)
        engagement_score = 0.65 * norm_log_engagement.get(username, 0.0) + 0.35 * norm_engagement_rate.get(username, 0.0)
        feature_map[username] = {
            "authority_score": round(authority_score, 6),
            "bridge_score": round(norm_betweenness.get(username, 0.0), 6),
            "engagement_score": round(engagement_score, 6),
            "follower_score": round(norm_follower_log.get(username, 0.0), 6),
            "weighted_degree_score": round(norm_weighted_degree.get(username, 0.0), 6),
            "pagerank_score": round(norm_pagerank.get(username, 0.0), 6),
            "engagement_rate_score": round(norm_engagement_rate.get(username, 0.0), 6),
        }

    return {
        "records": records,
        "feature_map": feature_map,
        "graph_summary": {
            "nodes": creator_graph.number_of_nodes(),
            "edges": creator_graph.number_of_edges(),
        },
    }


def _scenario_mode(intent: ProductIntent) -> str:
    direct_score_values = sorted((float(value) for value in intent.direct_category_scores.values()), reverse=True)
    if len(direct_score_values) >= 2 and direct_score_values[1] >= 2.0:
        return "bridge"
    if len(intent.direct_category_scores) <= 1 and not intent.semantic_signals.get("usage_contexts") and len(intent.semantic_signals.get("user_needs", [])) <= 1:
        return "authority"
    score_values = sorted((float(value) for value in intent.category_scores.values()), reverse=True)
    if len(score_values) < 2:
        return "authority"
    if score_values[1] >= score_values[0] * 0.75:
        return "bridge"
    return "authority"


def _build_dataset_reason(
    record: dict,
    matched_tags: list[str],
    category_fit: dict[str, float],
    score_breakdown: dict[str, float],
    intent: ProductIntent,
    mode: str,
) -> str:
    categories = ", ".join(record.get("categories", [])[:3]) or "kategori yok"
    matched_tag_text = ", ".join(f"#{tag}" for tag in matched_tags[:5]) or "dogrudan eslesen etiket bulunamadi"
    user_need_text = ", ".join(intent.semantic_signals.get("user_needs", [])[:3])
    usage_text = ", ".join(intent.semantic_signals.get("usage_contexts", [])[:3])
    product_type_text = ", ".join(intent.semantic_signals.get("product_types", [])[:3])
    if mode == "bridge":
        role_text = "Bu hesap birden fazla tema arasinda kopru olabilecek yapisal bir konuma sahip."
    else:
        role_text = "Bu hesap ilgili kategoride guclu etki ve etkilesim sinyalleri veriyor."

    semantic_parts: list[str] = []
    if user_need_text:
        semantic_parts.append(f"hedef kullanici sinyali: {user_need_text}.")
    if usage_text:
        semantic_parts.append(f"kullanim baglami: {usage_text}.")
    if product_type_text:
        semantic_parts.append(f"urun tipi: {product_type_text}.")
    semantic_text = " ".join(semantic_parts)

    return (
        f"{intent.query} icin {categories} ekseninde uygun gorunuyor. "
        f"{role_text} "
        f"{semantic_text} "
        f"Kategori uyumu {score_breakdown['category_fit_score']:.2f}, alaka skoru {score_breakdown['relevance_score']:.2f}. "
        f"Eslesen etiketler: {matched_tag_text}. "
        f"Ortalama etkilesim {record.get('avg_likes', 0):.0f} begeni ve {record.get('avg_comments', 0):.0f} yorum."
    )


def recommend_influencers_from_dataset(
    product_query: str,
    top_k: int = 5,
    min_posts: int = 3,
    min_followers: int = 500,
    follower_segments: list[str] | None = None,
    dataset_path: str | Path = DEFAULT_CREATOR_DATASET,
) -> dict:
    prepared = _prepare_creator_recommender_data(str(Path(dataset_path)))
    records = prepared["records"]
    feature_map = prepared["feature_map"]

    intent = infer_product_intent(product_query)
    product_terms = expand_category_keywords(intent.matched_categories)
    mode = _scenario_mode(intent)

    ranked: list[dict] = []

    for record in records:
        if record.get("posts", 0) < min_posts:
            continue
        if record.get("followers", 0) < min_followers:
            continue
        if follower_segments and record.get("follower_segment") not in set(follower_segments):
            continue

        tag_match_count, matched_tags = _tag_score_from_strings(record.get("top_hashtags", []), product_terms)
        category_fit = _category_fit(record.get("categories", []), intent.matched_categories)
        category_fit_score = category_fit["f1"]
        tag_match_score = min(tag_match_count / 3.0, 1.0)
        relevance_score = round(category_fit_score * 0.7 + tag_match_score * 0.3, 6)

        if category_fit["recall"] <= 0 and tag_match_count == 0:
            continue

        features = feature_map.get(record["username"], {})
        authority_score = features.get("authority_score", 0.0)
        bridge_score = features.get("bridge_score", 0.0)
        engagement_score = features.get("engagement_score", 0.0)
        follower_score = features.get("follower_score", 0.0)

        if mode == "bridge":
            total_score = (
                relevance_score * 0.38
                + bridge_score * 0.25
                + authority_score * 0.18
                + engagement_score * 0.12
                + follower_score * 0.07
            )
        else:
            total_score = (
                relevance_score * 0.50
                + authority_score * 0.22
                + engagement_score * 0.20
                + follower_score * 0.05
                + bridge_score * 0.03
            )

        primary_match_bonus = 0.08 if record.get("primary_category") in intent.matched_categories else 0.0
        total_score += primary_match_bonus

        score_breakdown = {
            "relevance_score": round(relevance_score, 4),
            "category_fit_score": round(category_fit_score, 4),
            "tag_match_score": round(tag_match_score, 4),
            "authority_score": round(authority_score, 4),
            "bridge_score": round(bridge_score, 4),
            "engagement_score": round(engagement_score, 4),
            "follower_score": round(follower_score, 4),
        }

        ranked.append(
            {
                "username": record["username"],
                "score": round(total_score, 4),
                "followers": int(record["followers"]),
                "follower_segment": record["follower_segment"],
                "avg_likes": record["avg_likes"],
                "avg_comments": record["avg_comments"],
                "posts_analyzed": record["posts"],
                "categories": record["categories"],
                "matched_tags": matched_tags,
                "scenario_mode": mode,
                "score_breakdown": score_breakdown,
                "reason": _build_dataset_reason(record, matched_tags, category_fit, score_breakdown, intent, mode),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["score"],
            item["score_breakdown"]["relevance_score"],
            item["score_breakdown"]["engagement_score"],
            item["followers"],
        ),
        reverse=True,
    )

    return {
        "product_query": product_query,
        "intent": {
            "matched_categories": intent.matched_categories,
            "matched_keywords": intent.matched_keywords,
            "category_scores": intent.category_scores,
            "direct_category_scores": intent.direct_category_scores,
            "semantic_signals": intent.semantic_signals,
            "mode": mode,
        },
        "recommendations": ranked[:top_k],
        "graph": prepared["graph_summary"],
        "dataset": {
            "path": str(dataset_path),
            "min_posts": min_posts,
            "min_followers": min_followers,
        },
    }


def save_recommendations(payload: dict, destination: str | Path) -> str:
    output_path = Path(destination)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)
