# backend/app/core/celery_app.py

import logging
from celery import Celery

# Import our centralized settings object
from .config import settings

# --- Configure Logging ---
logger = logging.getLogger(__name__)

# --- Create Celery Instance ---
# We instantiate Celery and give it the name of our main module.
celery_app = Celery(
    "tasks",  # A name for the celery app, can be anything.
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    # This line tells Celery to automatically discover task modules.
    # It will look for a `tasks.py` file in any of the apps listed in `include`.
    # For our structure, we will explicitly import our task files later.
    include=[
        'app.tasks.non_ai_conversions',
        'app.tasks.ai_conversions'
    ]
)

# --- Configure Celery from our settings object ---
# This line loads any celery-related configuration from our settings object.
# For example, if we had a setting like CELERY_TIMEZONE, it would be applied here.
celery_app.config_from_object(settings, namespace='CELERY')

# Optional: Set a result expiration time.
# After this time, the results of tasks will be deleted from the backend (Redis).
celery_app.conf.update(
    result_expires=3600, # 1 hour
)

logger.info("Celery application instance created.")
logger.info(f"Broker URL: {settings.CELERY_BROKER_URL}")
logger.info(f"Result Backend: {settings.CELERY_RESULT_BACKEND}")


# --- Main Block for Testing ---
if __name__ == '__main__':
    # You can run this file directly to test the connection to Redis.
    # Note: Use `python -m backend.app.core.celery_app` to run it
    # from the project root to handle relative imports correctly.
    
    logger.info("Pinging Redis to test connection...")
    try:
        # The `inspect()` method can be used to manage and monitor the workers.
        # Pinging is a simple way to check if the broker is reachable.
        i = celery_app.control.inspect()
        availability = i.ping()
        if not availability:
            logger.warning("No running Celery workers were found.")
        else:
            logger.info("Ping response from workers:")
            logger.info(availability)
        
        # A more direct way to test broker connection
        with celery_app.connection() as connection:
            logger.info("Successfully established connection to Redis.")
            
    except Exception as e:
        logger.critical(f"FATAL: Could not connect to the Celery broker (Redis).")
        logger.critical(f"Please ensure Redis server is running at {settings.REDIS_HOST}:{settings.REDIS_PORT}.")
        logger.critical(f"Error details: {e}")