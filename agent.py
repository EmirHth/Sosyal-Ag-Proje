import json

from openai import OpenAI

from apify_scraper import scrape_hashtag, scrape_profiles, summarize_scrape
from config import OPENAI_API_KEY, OPENAI_MODEL, PROCESSED_DIR


SYSTEM_PROMPT = """Sen bir influencer veri toplama ajansin. Gorevin:
1. Verilen seed influencer listesi icin scrape_instagram_profiles tool'unu cagirip post/hashtag verisi topla.
2. Toplanan veriyi summarize_scraped_data ile ozetle ve her kullanici icin TR kategori etiketleri uret (orn: "guzellik_kozmetik", "moda_yasam", "fitness_saglik", "yemek_mutfak", "seyahat", "teknoloji", "anne_bebek", "ev_yasam").
3. Bir kullanicinin top hashtag'lerinden yola cikarak hangi urun reklamlarina uygun oldugunu 1-2 cumle ile ozetle.
4. Sonuc olarak yapilandirilmis JSON dondur: [{username, followers, avg_engagement, categories, pitch}, ...].

Kural: Veri toplama yalnizca resmi Apify API ve izinli/acik kaynaklar uzerinden yapilir. Giris korumalari, guvenlik onlemleri veya platform kisitlari asilmaya calisilmaz. Kendi basina hashtag kesfi gerekirse scrape_hashtag tool'unu kullan.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scrape_instagram_profiles",
            "description": "Instagram profillerini ve son postlarini Apify uzerinden scrape eder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "usernames": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Instagram kullanici adlari (@ olmadan)",
                    },
                    "posts_per_profile": {"type": "integer", "default": 30},
                },
                "required": ["usernames"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_hashtag",
            "description": "Bir hashtag'in en yeni postlarini scrape eder (kesif icin).",
            "parameters": {
                "type": "object",
                "properties": {
                    "hashtag": {"type": "string", "description": "hashtag, # olmadan"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["hashtag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_scraped_data",
            "description": "Daha once scrape edilmis JSON dosyasini kullanici bazinda ozetler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "raw/ altindaki JSON dosyasinin yolu"},
                    "top_n_tags": {"type": "integer", "default": 15},
                },
                "required": ["path"],
            },
        },
    },
]

TOOL_IMPLS = {
    "scrape_instagram_profiles": lambda **kw: scrape_profiles(**kw),
    "scrape_hashtag": lambda **kw: scrape_hashtag(**kw),
    "summarize_scraped_data": lambda **kw: summarize_scrape(**kw),
}


def run_agent(seed_usernames: list[str], max_steps: int = 8) -> dict:
    client = OpenAI(api_key=OPENAI_API_KEY)

    user_task = (
        f"Su Turk influencer'lari scrape et ve her biri icin kategori + reklam pitch'i uret: "
        f"{seed_usernames}. Her profil icin 30 post yeterli."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for step in range(max_steps):
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            final = msg.content or ""
            out_path = PROCESSED_DIR / "agent_output.json"
            out_path.write_text(final, encoding="utf-8")
            return {"final_text": final, "output_path": str(out_path), "steps": step + 1}

        for tool_call in msg.tool_calls:
            fn = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            try:
                result = TOOL_IMPLS[fn](**args)
                content = json.dumps(result, ensure_ascii=False, default=str)[:8000]
            except Exception as exc:
                content = json.dumps({"error": str(exc)})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": content,
                }
            )

    return {"final_text": "max_steps reached", "steps": max_steps}
