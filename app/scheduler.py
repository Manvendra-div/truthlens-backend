from apscheduler.schedulers.background import BackgroundScheduler
from app.services.news_service import fetch_news

scheduler = BackgroundScheduler()

def start_scheduler():

    # runs every 2 days
    scheduler.add_job(fetch_news, "interval", days=2)
    scheduler.start()