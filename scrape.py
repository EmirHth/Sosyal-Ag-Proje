import argparse
import json
import sys
from pathlib import Path

from agent import run_agent
from apify_scraper import scrape_profiles, summarize_scrape
from cleaner import build_clean_creator_dataset
from config import PROCESSED_DIR, SEEDS_DIR
from dataset_builder import build_master_dataset, build_second_pass_seeds, run_category_discovery
from recommender import recommend_influencers, save_recommendations


def load_seed_usernames(seed_file: Path) -> list[str]:
    data = json.loads(seed_file.read_text(encoding="utf-8-sig"))
    return [row["username"] for row in data]


def safe_text(value: str) -> str:
    return value.encode("cp1254", errors="replace").decode("cp1254")


def main():
    parser = argparse.ArgumentParser(description="Instagram influencer scraper and recommender")
    parser.add_argument(
        "--mode",
        choices=["direct", "agent", "recommend", "discover", "master", "second-pass-seeds", "clean"],
        default="direct",
        help="direct: Apify scrape + local summary. agent: LLM-orchestrated multi-step run. recommend: urun bazli influencer oner. discover: kategori hashtag taramasi yap. master: butun verileri tek dataset'te birlestir. second-pass-seeds: ikinci tur profil scrape adaylarini sec. clean: profile scrape verilerinden temiz creator dataset uret.",
    )
    parser.add_argument(
        "--seeds",
        type=Path,
        default=SEEDS_DIR / "influencers_tr.json",
    )
    parser.add_argument("--posts", type=int, default=30)
    parser.add_argument("--summary-path", type=Path, help="recommend modunda kullanilacak ham scrape JSON yolu")
    parser.add_argument("--product", type=str, help="Ornek: 'kadin yuz serumu' veya 'silgi'")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--categories", nargs="*", help="discover modunda kosulacak kategoriler")
    parser.add_argument("--per-hashtag-limit", type=int, default=30, help="discover modunda hashtag basina cekilecek post sayisi")
    parser.add_argument("--segments", nargs="*", help="recommend modunda follower segment filtresi: nano micro mid macro mega")
    parser.add_argument("--per-category", type=int, default=6, help="second-pass-seeds modunda kategori basina secilecek aday sayisi")
    parser.add_argument("--max-total", type=int, default=40, help="second-pass-seeds modunda maksimum toplam aday")
    parser.add_argument("--min-posts", type=int, default=2, help="second-pass-seeds modunda aday secmek icin minimum post sayisi")
    args = parser.parse_args()

    if args.mode == "recommend":
        if not args.summary_path:
            raise SystemExit("--summary-path gerekli. Ornek: data/raw/scrape_123.json")
        if not args.product:
            raise SystemExit("--product gerekli. Ornek: --product 'kadin yuz serumu'")
        payload = recommend_influencers(
            summary_path=str(args.summary_path),
            product_query=args.product,
            top_k=args.top_k,
            follower_segments=args.segments,
        )
        out_path = PROCESSED_DIR / "recommendations.json"
        save_recommendations(payload, out_path)
        print(f"Recommendations saved to {out_path}")
        for index, rec in enumerate(payload["recommendations"], start=1):
            print(
                f"{index}. @{rec['username']} | score={rec['score']} | "
                f"followers={rec['followers']} | segment={rec['follower_segment']} | "
                f"matched_tags={', '.join(rec['matched_tags'][:4])}"
            )
        return

    if args.mode == "discover":
        payload = run_category_discovery(
            categories=args.categories,
            per_hashtag_limit=args.per_hashtag_limit,
        )
        print(f"Discovery finished with {payload['total_runs']} hashtag runs")
        for run in payload["runs"]:
            print(f"[{run['category']}] #{run['hashtag']} -> {run['count']} items | {run['path']}")
        return

    if args.mode == "master":
        payload = build_master_dataset()
        print(f"Master dataset rows: {payload['rows']}")
        print(f"JSON -> {payload['json_path']}")
        print(f"CSV -> {payload['csv_path']}")
        return

    if args.mode == "second-pass-seeds":
        payload = build_second_pass_seeds(
            per_category=args.per_category,
            max_total=args.max_total,
            min_posts=args.min_posts,
        )
        print(f"Second pass seeds: {payload['count']}")
        print(f"Path -> {payload['path']}")
        return

    if args.mode == "clean":
        payload = build_clean_creator_dataset()
        print(f"Classified profiles: {payload['classified_rows']}")
        print(f"Clean creators: {payload['clean_rows']}")
        print(f"Classified JSON -> {payload['classified_json']}")
        print(f"Clean JSON -> {payload['clean_json']}")
        print(f"Clean CSV -> {payload['clean_csv']}")
        return

    usernames = load_seed_usernames(args.seeds)
    print(f"Loaded {len(usernames)} seed usernames")

    if args.mode == "direct":
        result = scrape_profiles(usernames, posts_per_profile=args.posts)
        print(f"Scraped {result['count']} posts -> {result['path']}")
        summary = summarize_scrape(result["path"])
        print(f"Summarized {len(summary['users'])} users")
        for user in summary["users"]:
            tags = ", ".join(f"#{tag}({count})" for tag, count in user["top_hashtags"][:5])
            print(safe_text(f"  @{user['username']}: {user['posts']} posts | top: {tags}"))
        return

    out = run_agent(usernames)
    print(f"Agent finished in {out['steps']} steps")
    print(out.get("final_text", "")[:1000])


if __name__ == "__main__":
    main()
