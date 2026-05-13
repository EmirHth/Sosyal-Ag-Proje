import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SEEDS_DIR = DATA_DIR / "seeds"

for d in (RAW_DIR, PROCESSED_DIR, SEEDS_DIR):
    d.mkdir(parents=True, exist_ok=True)

OPENAI_MODEL = "gpt-4o-mini"
APIFY_ACTOR_ID = "apify/instagram-scraper"
