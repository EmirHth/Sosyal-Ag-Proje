import json
import re
import time
from pathlib import Path
from apify_client import ApifyClient

from config import APIFY_API_TOKEN, APIFY_ACTOR_ID, RAW_DIR
from taxonomy import classify_follower_segment, infer_creator_categories


def _client() -> ApifyClient:
    if not APIFY_API_TOKEN:
        raise RuntimeError(
            "APIFY_API_TOKEN not set. Sign up at apify.com, copy your token "
            "from Settings → Integrations, and add APIFY_API_TOKEN=... to .env"
        )
    return ApifyClient(APIFY_API_TOKEN)


def _extract_input_username(item: dict) -> str | None:
    input_url = item.get("inputUrl") or item.get("url")
    if not input_url:
        return None
    match = re.search(r"instagram\.com/([^/?#]+)/?", str(input_url))
    if not match:
        return None
    candidate = match.group(1).strip().lstrip("@")
    if candidate in {"p", "reel", "explore", "stories"}:
        return None
    return candidate or None


def _canonical_username(item: dict) -> str | None:
    input_username = _extract_input_username(item)
    owner_username = item.get("ownerUsername")
    username = item.get("username")

    if input_username and (input_username == owner_username or input_username == username):
        return input_username
    if input_username and username and not owner_username:
        return input_username
    return owner_username or username or input_username


def _resolve_followers(item: dict, canonical_username: str) -> int | None:
    owner_username = item.get("ownerUsername")
    username = item.get("username")

    if owner_username == canonical_username or username == canonical_username:
        for key in ("followersCount", "ownerFollowersCount"):
            value = item.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(value)

    metadata = item.get("metaData")
    if isinstance(metadata, dict):
        for key in ("followersCount", "ownerFollowersCount"):
            value = metadata.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(value)
    return None


def scrape_profiles(usernames: list[str], posts_per_profile: int = 30) -> dict:
    client = _client()

    run_input = {
        "directUrls": [f"https://www.instagram.com/{u.strip('@')}/" for u in usernames],
        "resultsType": "posts",
        "resultsLimit": posts_per_profile,
        "addParentData": True,
    }

    run = client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    ts = int(time.time())
    out_path = RAW_DIR / f"scrape_{ts}.json"
    out_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run_id": run["id"],
        "path": str(out_path),
        "count": len(items),
        "usernames": usernames,
    }


def scrape_hashtag(hashtag: str, limit: int = 50) -> dict:
    client = _client()

    run_input = {
        "directUrls": [f"https://www.instagram.com/explore/tags/{hashtag.lstrip('#')}/"],
        "resultsType": "posts",
        "resultsLimit": limit,
    }

    run = client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    ts = int(time.time())
    out_path = RAW_DIR / f"hashtag_{hashtag}_{ts}.json"
    out_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run_id": run["id"],
        "path": str(out_path),
        "count": len(items),
        "hashtag": hashtag,
    }


def summarize_scrape(path: str, top_n_tags: int = 15) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    by_user: dict[str, dict] = {}

    for item in data:
        if item.get("error") == "no_items":
            continue
        user = _canonical_username(item)
        if not user:
            continue
        rec = by_user.setdefault(user, {
            "username": user,
            "posts": 0,
            "likes_sum": 0,
            "comments_sum": 0,
            "hashtag_counts": {},
            "followers": None,
        })
        rec["posts"] += 1
        rec["likes_sum"] += item.get("likesCount") or 0
        rec["comments_sum"] += item.get("commentsCount") or 0
        followers = _resolve_followers(item, user)
        if followers:
            rec["followers"] = followers
        for tag in item.get("hashtags") or []:
            rec["hashtag_counts"][tag] = rec["hashtag_counts"].get(tag, 0) + 1

    for rec in by_user.values():
        sorted_tags = sorted(rec["hashtag_counts"].items(), key=lambda x: -x[1])
        rec["top_hashtags"] = sorted_tags[:top_n_tags]
        del rec["hashtag_counts"]
        rec["avg_likes"] = rec["likes_sum"] / rec["posts"] if rec["posts"] else 0
        rec["avg_comments"] = rec["comments_sum"] / rec["posts"] if rec["posts"] else 0
        rec["categories"] = infer_creator_categories([tag for tag, _ in rec["top_hashtags"]])
        rec["follower_segment"] = classify_follower_segment(rec["followers"])

    return {"users": list(by_user.values()), "total_posts": len(data)}
