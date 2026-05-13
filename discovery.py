from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from taxonomy import classify_follower_segment, infer_creator_categories, normalize_text


BUSINESS_HINTS = {
    "store",
    "shop",
    "market",
    "kozmetik",
    "cosmetic",
    "cosmetics",
    "official",
    "haber",
    "news",
    "center",
    "clinic",
    "klinik",
    "pharmacy",
    "eczane",
    "boutique",
    "butik",
    "shop",
    "mall",
}


def discover_candidates(paths: list[str], min_posts: int = 1, top_k: int = 50) -> dict:
    by_user: dict[str, dict] = {}

    for path in paths:
        records = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in records:
            username = item.get("ownerUsername") or item.get("username")
            if not username:
                continue

            rec = by_user.setdefault(
                username,
                {
                    "username": username,
                    "posts": 0,
                    "likes_sum": 0,
                    "comments_sum": 0,
                    "hashtags": defaultdict(int),
                    "sources": set(),
                },
            )
            rec["posts"] += 1
            rec["likes_sum"] += max(item.get("likesCount") or 0, 0)
            rec["comments_sum"] += max(item.get("commentsCount") or 0, 0)
            rec["sources"].add(Path(path).name)
            for tag in item.get("hashtags") or []:
                rec["hashtags"][tag] += 1

    candidates: list[dict] = []
    for rec in by_user.values():
        if rec["posts"] < min_posts:
            continue
        top_hashtags = sorted(rec["hashtags"].items(), key=lambda pair: (-pair[1], normalize_text(pair[0])))[:10]
        categories = infer_creator_categories([tag for tag, _ in top_hashtags])
        score = rec["posts"] * 2 + rec["likes_sum"] * 0.02 + rec["comments_sum"] * 0.2
        business_likelihood = score_business_likelihood(rec["username"], [tag for tag, _ in top_hashtags])
        candidates.append(
            {
                "username": rec["username"],
                "posts": rec["posts"],
                "avg_likes": round(rec["likes_sum"] / rec["posts"], 2),
                "avg_comments": round(rec["comments_sum"] / rec["posts"], 2),
                "categories": categories,
                "follower_segment": classify_follower_segment(None),
                "top_hashtags": top_hashtags,
                "sources": sorted(rec["sources"]),
                "business_likelihood": business_likelihood,
                "score": round(score, 2),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return {"candidates": candidates[:top_k], "total_candidates": len(candidates)}


def save_candidates(payload: dict, path: str | Path) -> str:
    output_path = Path(path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)


def score_business_likelihood(username: str, hashtags: list[str]) -> float:
    score = 0.0
    normalized_username = normalize_text(username)
    normalized_tags = [normalize_text(tag) for tag in hashtags]

    for hint in BUSINESS_HINTS:
        if hint in normalized_username:
            score += 1.0
        if any(hint in tag for tag in normalized_tags):
            score += 0.4

    if any(char.isdigit() for char in username):
        score += 0.2
    if normalized_username.count("_") >= 2:
        score += 0.2

    return round(score, 2)


def select_second_pass_usernames(
    candidates_payload: dict,
    per_category: int = 6,
    max_total: int = 40,
    max_business_likelihood: float = 1.2,
    exclude_usernames: set[str] | None = None,
) -> list[dict]:
    selected: list[dict] = []
    seen_usernames: set[str] = set()
    category_counts: dict[str, int] = defaultdict(int)
    excluded = {normalize_text(username) for username in (exclude_usernames or set()) if username}

    sorted_candidates = sorted(
        candidates_payload.get("candidates", []),
        key=lambda item: (item.get("business_likelihood", 99), -item.get("score", 0), item.get("username", "")),
    )

    for candidate in sorted_candidates:
        if candidate.get("business_likelihood", 99) > max_business_likelihood:
            continue
        username = candidate["username"]
        if normalize_text(username) in excluded:
            continue
        if username in seen_usernames:
            continue

        categories = candidate.get("categories", []) or ["genel"]
        primary = categories[0]
        if category_counts[primary] >= per_category:
            continue

        selected.append(candidate)
        seen_usernames.add(username)
        category_counts[primary] += 1

        if len(selected) >= max_total:
            break

    return selected
