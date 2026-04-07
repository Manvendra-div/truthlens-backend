# app/services/news_service.py
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.post import Post
from app.services.model_service import predict_news
from app.services.dedup_service import check_duplicate, compute_hash
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWSAPIORG_API")
SYSTEM_USER_ID = 2

def fetch_news_articles():
    """Sync HTTP call — keep this sync, it's just an API request."""
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "category": "technology",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"[news_service] NewsAPI error: {response.status_code} {response.text}")
        return []
    return response.json().get("articles", [])


async def fetch_news():
    """Async DB operations — converted to async."""
    articles = fetch_news_articles()

    if not articles:
        print("[news_service] No articles returned.")
        return

    saved = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        try:
            for article in articles:
                title       = article.get("title", "").strip()
                description = article.get("description", "") or ""

                if not title or title == "[Removed]":
                    continue

                content = description.strip()

                # ── duplicate check ──────────────────────────────────────
                result = await check_duplicate(db, title, content)  # ← needs to be async too
                if result.is_duplicate:
                    print(f"[news_service] Skipping duplicate: {title[:60]}")
                    skipped += 1
                    continue

                # ── prediction ───────────────────────────────────────────
                full_text  = f"{title} {content}"
                prediction = predict_news(full_text)

                # ── build post ───────────────────────────────────────────
                post = Post(
                    title           = title,
                    content         = content,
                    prediction      = prediction["label"],
                    fake_confidence = prediction["fake_confidence"],
                    real_confidence = prediction["real_confidence"],
                    author_id       = SYSTEM_USER_ID,
                    content_hash    = compute_hash(title, content),
                    created_at      = datetime.now(timezone.utc),
                )
                db.add(post)
                saved += 1

            await db.commit()
            print(f"[news_service] saved={saved} skipped_duplicates={skipped}")

        except Exception as e:
            await db.rollback()
            print(f"[news_service] Error: {e}")
            raise