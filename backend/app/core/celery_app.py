# backend/app/core/celery_app.py (The Final, Corrected Path Version)

import logging
from celery import Celery

from .config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    # --- CRUCIAL FIX ---
    # We now provide the full path from the project root, where the celery command is run.
    # 'backend.app.tasks...' tells Celery to look inside the 'backend' folder first.
    include=[
        'backend.app.tasks.non_ai_conversions',
        'backend.app.tasks.ai_conversions'
    ]
)

celery_app.config_from_object(settings, namespace='CELERY')

celery_app.conf.update(
    result_expires=3600,
)

logger.info("Celery application instance created.")
logger.info(f"Broker URL: {settings.CELERY_BROKER_URL}")
logger.info(f"Result Backend: {settings.CELERY_RESULT_BACKEND}")

if __name__ == '__main__':
    logger.info("Pinging Redis to test connection...")
    try:
        i = celery_app.control.inspect()
        availability = i.ping()
        if not availability:
            logger.warning("No running Celery workers were found.")
        else:
            logger.info(f"Ping response from workers: {availability}")
        
        with celery_app.connection() as connection:
            logger.info("Successfully established connection to Redis.")
            
    except Exception as e:
        logger.critical(f"FATAL: Could not connect to the Celery broker (Redis).")
        logger.critical(f"Error details: {e}")