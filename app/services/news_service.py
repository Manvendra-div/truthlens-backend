# app/services/news_service.py

import requests
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.post import Post
from app.services.model_service import predict_news
from app.services.dedup_service import check_duplicate, compute_hash
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWSAPIORG_API")
SYSTEM_USER_ID = 2


def fetch_news():
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
        return

    data = response.json()
    articles = data.get("articles", [])

    if not articles:
        print("[news_service] No articles returned.")
        return

    db: Session = SessionLocal()
    saved = 0
    skipped = 0

    try:
        for article in articles:
            title       = article.get("title", "").strip()
            description = article.get("description", "") or ""

            # skip removed/empty articles
            if not title or title == "[Removed]":
                continue

            content = description.strip()

            # ── duplicate check ──────────────────────────────────────
            result = check_duplicate(db, title, content)
            if result.is_duplicate:
                print(f"[news_service] Skipping duplicate: {title[:60]}")
                skipped += 1
                continue

            # ── prediction ───────────────────────────────────────────
            full_text  = f"{title} {content}"
            prediction = predict_news(full_text)

            # ── build post ───────────────────────────────────────────
            post = Post(
                title            = title,
                content          = content,
                prediction       = prediction["label"],        # ← correct field
                fake_confidence  = prediction["fake_confidence"],
                real_confidence  = prediction["real_confidence"],
                author_id        = SYSTEM_USER_ID,             # ← correct field
                content_hash     = compute_hash(title, content),
                created_at       = datetime.now(timezone.utc),
            )

            db.add(post)
            saved += 1

        db.commit()
        print(f"[news_service] saved={saved} skipped_duplicates={skipped}")

    except Exception as e:
        db.rollback()
        print(f"[news_service] Error: {e}")
        raise

    finally:
        db.close()