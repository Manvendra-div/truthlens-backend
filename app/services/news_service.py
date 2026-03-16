import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.post import Post
from app.services.model_service import predict_news

NEWS_API_KEY = "76e6f976a95c4228b7761f2d0a0ec95e"


def fetch_news():

    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "country": "us",
        "category": "technology",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    articles = data.get("articles", [])

    db: Session = SessionLocal()

    try:
        for article in articles:

            title = article.get("title")
            description = article.get("description")
            article_url = article.get("url")

            if not title:
                continue

            content = description or ""

            # prevent duplicates
            exists = db.query(Post).filter(Post.source_url == article_url).first()
            if exists:
                continue

            full_text = f"{title} {content}"

            prediction = predict_news(full_text)

            post = Post(
                title=title,
                content=content,
                source_url=article_url,
                user_id=1,
                prediction_label=prediction["label"],
                fake_confidence=prediction["confidence"]["fake"],
                real_confidence=prediction["confidence"]["real"]
            )

            db.add(post)

        db.commit()

    finally:
        db.close()