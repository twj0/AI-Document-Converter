# backend/app/core/config.py

import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Determine Base Directory ---
# This allows us to define paths relative to the project root.
# The project root is assumed to be the parent directory of the 'backend' folder.
# backend/ -> Project Root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Main configuration class for the application.
    It uses Pydantic to enforce type hints and validate data.
    Values are loaded from a .env file.
    """
    # --- Environment Configuration ---
    # The `model_config` attribute tells Pydantic where to find the .env file.
    # We specify a .env file located in the 'backend' directory.
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / 'backend' / '.env',
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra fields from the .env file
    )

    # --- Project Metadata ---
    PROJECT_NAME: str = "AI Document Converter Pro"
    API_V1_STR: str = "/api/v1"

    # --- AI Provider Configuration ---
    # The user can choose which AI provider to use. Defaults to "gemini".
    AI_PROVIDER: str = Field("gemini", description="AI provider to use ('gemini', 'openai', etc.)")
    
    # --- API Keys ---
    # These are loaded from the .env file. They are optional because the user
    # might only want to use one provider, but the app will fail gracefully
    # if a provider is selected without its corresponding key.
    GEMINI_API_KEY: Optional[str] = Field(None, description="API Key for Google Gemini")
    OPENAI_API_KEY: Optional[str] = Field(None, description="API Key for OpenAI")
    ZHIPU_API_KEY: Optional[str] = Field(None, description="API Key for Zhipu AI (GLM)")

    # --- Model Names ---
    # Default model names for each provider. Can be overridden by .env variables.
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash-latest"
    OPENAI_MODEL_NAME: str = "gpt-4o"
    GLM_MODEL_NAME: str = "glm-4-flash"

    # --- Celery and Redis Configuration ---
    # These provide connection details for our background task queue.
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    CELERY_BROKER_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    CELERY_RESULT_BACKEND: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

    # --- File Paths ---
    # Defines where temporary files and final outputs are stored.
    # It's good practice to make these configurable.
    TEMP_FILE_DIR: Path = BASE_DIR / "temp_files"
    OUTPUT_FILE_DIR: Path = BASE_DIR / "output_files"


# --- Instantiate Settings ---
# This single `settings` object will be imported and used throughout the application.
try:
    settings = Settings()
    
    # --- Post-Instantiation Validation ---
    # We can add checks here to ensure the configuration is logical.
    logger.info("Application settings loaded successfully.")
    logger.info(f"Selected AI Provider: {settings.AI_PROVIDER.upper()}")

    # Check if the API key for the selected provider is actually set.
    selected_provider_key = {
        "gemini": settings.GEMINI_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "zhipuai": settings.ZHIPU_API_KEY,
    }.get(settings.AI_PROVIDER.lower())

    if not selected_provider_key:
        logger.warning(
            f"The selected AI provider is '{settings.AI_PROVIDER}', but its API key is NOT set "
            f"in the .env file. AI-based conversions will fail."
        )

except Exception as e:
    logger.critical(f"FATAL ERROR: Could not load application settings. Reason: {e}")
    # In a real app, you might exit here if the config is invalid.
    # For now, we create a default object to allow the app to import.
    settings = Settings()


# --- Main Block for Testing ---
if __name__ == '__main__':
    # You can run this file directly to check your configuration.
    print("--- Loaded Application Settings ---")
    # The `model_dump()` method provides a dictionary representation of the settings.
    print(settings.model_dump_json(indent=2))
    print("---------------------------------")
    # You can also access individual settings like an object attribute.
    print(f"Project Name: {settings.PROJECT_NAME}")
    print(f"Using Redis at: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"Temporary file directory: {settings.TEMP_FILE_DIR}")