from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from apify_scraper import scrape_hashtag, summarize_scrape
from config import PROCESSED_DIR, RAW_DIR
from discovery import discover_candidates, select_second_pass_usernames
from taxonomy import get_discovery_hashtags


def load_existing_profile_usernames() -> set[str]:
    master_path = PROCESSED_DIR / "master_influencer_dataset.json"
    if not master_path.exists():
        return set()

    rows = json.loads(master_path.read_text(encoding="utf-8"))
    return {
        row.get("username", "").strip().lower()
        for row in rows
        if row.get("source_type") == "profile_scrape" and row.get("username")
    }


def run_category_discovery(
    categories: list[str] | None = None,
    per_hashtag_limit: int = 30,
) -> dict:
    selected = get_discovery_hashtags(categories)
    runs: list[dict] = []

    for category, hashtags in selected.items():
        for hashtag in hashtags:
            result = scrape_hashtag(hashtag, limit=per_hashtag_limit)
            result["category"] = category
            runs.append(result)

    output = {
        "categories": list(selected.keys()),
        "runs": runs,
        "total_runs": len(runs),
    }
    out_path = PROCESSED_DIR / "discovery_runs.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def build_master_dataset() -> dict:
    dataset_rows: list[dict] = []

    for raw_path in sorted(RAW_DIR.glob("scrape_*.json")):
        summary = summarize_scrape(str(raw_path))
        for user in summary.get("users", []):
            dataset_rows.append(
                {
                    "username": user["username"],
                    "source_type": "profile_scrape",
                    "source_file": raw_path.name,
                    "posts": user.get("posts", 0),
                    "followers": user.get("followers"),
                    "follower_segment": user.get("follower_segment", "unknown"),
                    "avg_likes": round(user.get("avg_likes", 0), 2),
                    "avg_comments": round(user.get("avg_comments", 0), 2),
                    "categories": ",".join(user.get("categories", [])),
                    "top_hashtags": ",".join(tag for tag, _ in user.get("top_hashtags", [])[:10]),
                }
            )

    hashtag_paths = [str(path) for path in sorted(RAW_DIR.glob("hashtag_*.json"))]
    if hashtag_paths:
        discovered = discover_candidates(hashtag_paths, min_posts=1, top_k=500)
        for candidate in discovered.get("candidates", []):
            dataset_rows.append(
                {
                    "username": candidate["username"],
                    "source_type": "hashtag_discovery",
                    "source_file": ",".join(candidate.get("sources", [])),
                    "posts": candidate.get("posts", 0),
                    "followers": None,
                    "follower_segment": candidate.get("follower_segment", "unknown"),
                    "avg_likes": candidate.get("avg_likes", 0),
                    "avg_comments": candidate.get("avg_comments", 0),
                    "categories": ",".join(candidate.get("categories", [])),
                    "top_hashtags": ",".join(tag for tag, _ in candidate.get("top_hashtags", [])[:10]),
                }
            )

    by_key: dict[tuple[str, str], dict] = {}
    for row in dataset_rows:
        key = (row["username"], row["source_type"])
        by_key[key] = row

    deduped_rows = list(by_key.values())
    deduped_rows.sort(key=lambda row: (row["source_type"], row["username"]))

    json_path = PROCESSED_DIR / "master_influencer_dataset.json"
    csv_path = PROCESSED_DIR / "master_influencer_dataset.csv"

    json_path.write_text(json.dumps(deduped_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(deduped_rows).to_csv(csv_path, index=False)

    return {
        "rows": len(deduped_rows),
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }


def build_second_pass_seeds(
    per_category: int = 6,
    max_total: int = 40,
    min_posts: int = 2,
) -> dict:
    hashtag_paths = [str(path) for path in sorted(RAW_DIR.glob("hashtag_*.json"))]
    discovered = discover_candidates(hashtag_paths, min_posts=min_posts, top_k=500)
    existing_profiles = load_existing_profile_usernames()
    selected = select_second_pass_usernames(
        discovered,
        per_category=per_category,
        max_total=max_total,
        exclude_usernames=existing_profiles,
    )

    payload = [
        {
            "username": candidate["username"],
            "expected_category": (candidate.get("categories") or ["genel"])[0],
            "business_likelihood": candidate.get("business_likelihood", 0),
            "score": candidate.get("score", 0),
        }
        for candidate in selected
    ]

    out_path = RAW_DIR.parent / "seeds" / "second_pass_candidates.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "count": len(payload),
        "path": str(out_path),
    }
