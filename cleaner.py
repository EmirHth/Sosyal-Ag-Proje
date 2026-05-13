from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import PROCESSED_DIR
from taxonomy import normalize_text


BUSINESS_HINTS = {
    "store",
    "shop",
    "market",
    "kozmetik",
    "cosmetic",
    "cosmetics",
    "boutique",
    "butik",
    "gadget",
    "marketler",
    "official",
    "akademi",
    "academy",
    "kurst",
    "kurs",
    "clinic",
    "center",
    "merkezi",
    "phia",
}

MEDIA_HINTS = {
    "haber",
    "news",
    "gazete",
    "media",
    "podcast",
    "magazine",
    "dergi",
}

CREATOR_HINTS = {
    "ugc",
    "studygram",
    "outfit",
    "kombin",
    "skincare",
    "fitness",
    "recipe",
    "tarif",
    "yoga",
    "pilates",
    "catlover",
    "dog",
    "artist",
    "illustration",
}


def classify_account(row: dict) -> tuple[str, float, dict]:
    username = normalize_text(row.get("username", ""))
    tags = [normalize_text(tag) for tag in str(row.get("top_hashtags", "")).split(",") if tag]
    categories = [normalize_text(cat) for cat in str(row.get("categories", "")).split(",") if cat]
    followers = row.get("followers") or 0
    avg_likes = row.get("avg_likes") or 0
    avg_comments = row.get("avg_comments") or 0

    business_score = 0.0
    media_score = 0.0
    creator_score = 0.0

    for hint in BUSINESS_HINTS:
        if hint in username:
            business_score += 1.2
        if any(hint in tag for tag in tags):
            business_score += 0.3

    for hint in MEDIA_HINTS:
        if hint in username:
            media_score += 1.4
        if any(hint in tag for tag in tags):
            media_score += 0.4

    for hint in CREATOR_HINTS:
        if hint in username:
            creator_score += 0.8
        if any(hint in tag for tag in tags):
            creator_score += 0.5

    if any(cat in {"guzellik_kozmetik", "moda_yasam", "fitness_saglik", "yemek_mutfak", "egitim_kariyer"} for cat in categories):
        creator_score += 0.4

    if followers and avg_likes:
        engagement_ratio = (avg_likes + avg_comments * 3) / max(followers, 1)
        if engagement_ratio > 0.02:
            creator_score += 0.8
        elif engagement_ratio < 0.002:
            business_score += 0.3

    if followers and followers < 100_000:
        creator_score += 0.2
    if followers and followers > 500_000 and avg_likes < 100:
        media_score += 0.4

    if media_score >= max(business_score, creator_score) and media_score >= 1.2:
        account_type = "media"
        confidence = min(0.95, 0.55 + media_score / 5)
    elif business_score > creator_score and business_score >= 1.2:
        account_type = "business"
        confidence = min(0.95, 0.55 + business_score / 5)
    elif creator_score >= business_score and creator_score >= 0.8:
        account_type = "creator"
        confidence = min(0.95, 0.55 + creator_score / 5)
    else:
        account_type = "uncertain"
        confidence = 0.4

    return account_type, round(confidence, 2), {
        "creator_score": round(creator_score, 2),
        "business_score": round(business_score, 2),
        "media_score": round(media_score, 2),
    }


def build_clean_creator_dataset(master_dataset_path: str | Path | None = None) -> dict:
    source_path = Path(master_dataset_path or (PROCESSED_DIR / "master_influencer_dataset.json"))
    rows = json.loads(source_path.read_text(encoding="utf-8"))

    enriched_rows: list[dict] = []
    clean_rows: list[dict] = []

    for row in rows:
        if row.get("source_type") != "profile_scrape":
            continue
        account_type, confidence, scores = classify_account(row)
        enriched = dict(row)
        enriched["account_type"] = account_type
        enriched["account_confidence"] = confidence
        enriched.update(scores)
        enriched_rows.append(enriched)

        if account_type == "creator":
            clean_rows.append(enriched)

    classified_json = PROCESSED_DIR / "classified_profiles.json"
    clean_json = PROCESSED_DIR / "clean_creator_dataset.json"
    clean_csv = PROCESSED_DIR / "clean_creator_dataset.csv"

    classified_json.write_text(json.dumps(enriched_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    clean_json.write_text(json.dumps(clean_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(clean_rows).to_csv(clean_csv, index=False)

    return {
        "classified_rows": len(enriched_rows),
        "clean_rows": len(clean_rows),
        "classified_json": str(classified_json),
        "clean_json": str(clean_json),
        "clean_csv": str(clean_csv),
    }
