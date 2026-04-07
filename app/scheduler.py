import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.news_service import fetch_news

def run_fetch_news():
    asyncio.run(fetch_news())  # ✅ run async function from sync scheduler

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_fetch_news, "interval", minutes=30)
    scheduler.start()
    print("[scheduler] Started.")