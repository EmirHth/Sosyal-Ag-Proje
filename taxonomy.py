from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


TAXONOMY_PATH = Path(__file__).resolve().parent / "data" / "taxonomy" / "product_taxonomy.json"
CATEGORY_DIR = Path(__file__).resolve().parent / "data" / "taxonomy" / "categories"


@dataclass(frozen=True)
class ProductIntent:
    query: str
    normalized_query: str
    matched_categories: list[str]
    matched_keywords: list[str]
    category_scores: dict[str, float]
    direct_category_scores: dict[str, float]
    semantic_signals: dict[str, list[str]]


def _load_taxonomy_payload() -> dict[str, Any]:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def _generate_category_terms(category_payload: dict[str, Any]) -> list[str]:
    terms: set[str] = set()

    for item in category_payload.get("core_terms", []):
        if isinstance(item, str) and item.strip():
            terms.add(item.strip())

    nouns = [item.strip() for item in category_payload.get("product_nouns", []) if str(item).strip()]
    descriptors = [item.strip() for item in category_payload.get("descriptors", []) if str(item).strip()]
    audiences = [item.strip() for item in category_payload.get("audiences", []) if str(item).strip()]
    contexts = [item.strip() for item in category_payload.get("contexts", []) if str(item).strip()]
    suffixes = [item.strip() for item in category_payload.get("suffixes", []) if str(item).strip()]

    for noun in nouns:
        for descriptor in descriptors:
            terms.add(f"{descriptor} {noun}")
        for audience in audiences:
            terms.add(f"{audience} {noun}")
        for context in contexts:
            terms.add(f"{context} {noun}")
        for suffix in suffixes:
            terms.add(f"{noun} {suffix}")
        for descriptor in descriptors:
            for suffix in suffixes:
                terms.add(f"{descriptor} {noun} {suffix}")
        for audience in audiences:
            for suffix in suffixes:
                terms.add(f"{audience} {noun} {suffix}")
        for audience in audiences:
            for descriptor in descriptors[: min(len(descriptors), 6)]:
                terms.add(f"{audience} {descriptor} {noun}")

    return sorted(terms)


def _load_category_keyword_sets(
    category_dir: Path,
    fallback: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    if not category_dir.exists():
        return fallback, fallback

    high_precision: dict[str, list[str]] = {}
    broad: dict[str, list[str]] = {}
    for path in sorted(category_dir.glob("*.json")):
        category_payload = json.loads(path.read_text(encoding="utf-8"))
        category_name = str(category_payload.get("category", path.stem)).strip()
        if not category_name:
            continue
        high_precision[category_name] = [item.strip() for item in category_payload.get("core_terms", []) if str(item).strip()]
        broad[category_name] = _generate_category_terms(category_payload)

    return (high_precision or fallback, broad or fallback)


_TAXONOMY = _load_taxonomy_payload()

HIGH_PRECISION_CATEGORY_KEYWORDS, CATEGORY_KEYWORDS = _load_category_keyword_sets(CATEGORY_DIR, _TAXONOMY["category_keywords"])
HASHTAG_CATEGORY_HINTS: dict[str, list[str]] = _TAXONOMY["hashtag_category_hints"]
DISCOVERY_HASHTAGS: dict[str, list[str]] = _TAXONOMY["discovery_hashtags"]
WEIGHTED_PRODUCT_HINTS: dict[str, dict[str, float]] = _TAXONOMY["weighted_product_hints"]
USER_NEED_SIGNALS: dict[str, dict[str, float]] = _TAXONOMY["user_need_signals"]
USAGE_CONTEXT_SIGNALS: dict[str, dict[str, float]] = _TAXONOMY["usage_context_signals"]
PRODUCT_TYPE_SIGNALS: dict[str, dict[str, float]] = _TAXONOMY["product_type_signals"]


def normalize_text(value: str) -> str:
    replacements = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
            "Ç": "c",
            "Ğ": "g",
            "İ": "i",
            "Ö": "o",
            "Ş": "s",
            "Ü": "u",
        }
    )
    return value.lower().translate(replacements).strip()


def _tokenize_text(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", normalize_text(value)) if token]


def _contains_keyword(query: str, keyword: str) -> bool:
    query_tokens = _tokenize_text(query)
    keyword_tokens = _tokenize_text(keyword)
    if not query_tokens or not keyword_tokens:
        return False

    window = len(keyword_tokens)
    for start in range(0, len(query_tokens) - window + 1):
        if query_tokens[start : start + window] == keyword_tokens:
            return True
    return False


def _apply_weighted_signal(
    normalized_query: str,
    signal_map: dict[str, dict[str, float]],
    scores: Counter[str],
    bucket: list[str],
) -> None:
    for hint, weighted_categories in signal_map.items():
        normalized_hint = normalize_text(hint)
        if not _contains_keyword(normalized_query, normalized_hint):
            continue
        bucket.append(hint)
        for category, weight in weighted_categories.items():
            scores[category] += weight


def infer_product_intent(query: str) -> ProductIntent:
    normalized = normalize_text(query)
    scores: Counter[str] = Counter()
    direct_scores: Counter[str] = Counter()
    matched_keywords: list[str] = []
    semantic_signals = {
        "user_needs": [],
        "usage_contexts": [],
        "product_types": [],
    }
    normalized_high_precision = {
        category: {normalize_text(item) for item in keywords}
        for category, keywords in HIGH_PRECISION_CATEGORY_KEYWORDS.items()
    }

    for category, keywords in HIGH_PRECISION_CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)
            if _contains_keyword(normalized, normalized_keyword):
                keyword_score = max(2, len(_tokenize_text(normalized_keyword)))
                scores[category] += keyword_score
                direct_scores[category] += keyword_score
                matched_keywords.append(keyword)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)
            if _contains_keyword(normalized, normalized_keyword):
                if normalized_keyword in normalized_high_precision.get(category, set()):
                    continue
                scores[category] += 0.45
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

    for hint, weighted_categories in WEIGHTED_PRODUCT_HINTS.items():
        normalized_hint = normalize_text(hint)
        if not _contains_keyword(normalized, normalized_hint):
            continue
        matched_keywords.append(hint)
        for category, weight in weighted_categories.items():
            scores[category] += weight

    _apply_weighted_signal(normalized, USER_NEED_SIGNALS, scores, semantic_signals["user_needs"])
    _apply_weighted_signal(normalized, USAGE_CONTEXT_SIGNALS, scores, semantic_signals["usage_contexts"])
    _apply_weighted_signal(normalized, PRODUCT_TYPE_SIGNALS, scores, semantic_signals["product_types"])

    if not scores:
        tokens = [token for token in normalized.replace(",", " ").split() if token]
        for token in tokens:
            for category, keywords in CATEGORY_KEYWORDS.items():
                if any(token == normalize_text(keyword) for keyword in keywords):
                    scores[category] += 1
                    matched_keywords.append(token)

    category_scores = {name: round(float(score), 4) for name, score in scores.most_common()}
    direct_category_scores = {name: round(float(score), 4) for name, score in direct_scores.most_common()}

    if category_scores:
        top_score = max(category_scores.values())
        threshold = max(1.0, top_score * 0.25)
        categories = [name for name, score in category_scores.items() if score >= threshold][:3]
    else:
        categories = ["genel"]
        category_scores = {"genel": 0.0}

    return ProductIntent(
        query=query,
        normalized_query=normalized,
        matched_categories=categories,
        matched_keywords=sorted(set(matched_keywords)),
        category_scores=category_scores,
        direct_category_scores=direct_category_scores,
        semantic_signals=semantic_signals,
    )


def expand_category_keywords(categories: Iterable[str]) -> list[str]:
    expanded: list[str] = []
    for category in categories:
        expanded.extend(HASHTAG_CATEGORY_HINTS.get(category, []))
        expanded.extend(CATEGORY_KEYWORDS.get(category, []))
    return sorted({normalize_text(item) for item in expanded if item})


def infer_creator_categories(hashtags: Iterable[str], top_k: int = 3) -> list[str]:
    scores: Counter[str] = Counter()
    normalized_tags = [normalize_text(str(tag).lstrip("#")) for tag in hashtags if str(tag).strip()]

    for category, hints in HASHTAG_CATEGORY_HINTS.items():
        normalized_hints = [normalize_text(hint) for hint in hints]
        for tag in normalized_tags:
            for hint in normalized_hints:
                if hint and (hint in tag or tag in hint):
                    scores[category] += 1
                    break

    if not scores:
        return ["genel"]
    return [category for category, _ in scores.most_common(top_k)]


def get_discovery_hashtags(categories: Iterable[str] | None = None) -> dict[str, list[str]]:
    if categories is None:
        categories = DISCOVERY_HASHTAGS.keys()
    selected: dict[str, list[str]] = {}
    for category in categories:
        if category in DISCOVERY_HASHTAGS:
            selected[category] = DISCOVERY_HASHTAGS[category]
    return selected


def classify_follower_segment(followers: int | None) -> str:
    if followers is None or followers <= 0:
        return "unknown"
    if followers < 10_000:
        return "nano"
    if followers < 100_000:
        return "micro"
    if followers < 500_000:
        return "mid"
    if followers < 1_000_000:
        return "macro"
    return "mega"
