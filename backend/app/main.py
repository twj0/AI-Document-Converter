# backend/app/main.py

import logging
from fastapi import FastAPI
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# Import the centralized settings object
from .core.config import settings

# Import the main API router we assembled in the previous step
from .api.v1.api import api_router


# --- Configure Logging ---
# Although other modules have logging, it's good practice to have a
# basic configuration at the main entry point as well.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Create FastAPI Application Instance ---
# The title and version are loaded from our settings object, which centralizes configuration.
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="A professional-grade API for converting documents using AI.",
    # You can add more metadata here
    # # The openapi_url is the path to the auto-generated API schema
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- 2. Add CORS Middleware ---
# This is the new block of code that enables Cross-Origin requests.
# It tells the backend to allow requests from our frontend development server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # The address of our frontend
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)


# --- Event Handler: on_startup ---
# This is a good place for tasks that need to run once when the server starts.
@app.on_event("startup")
def on_startup():
    """
    Perform application startup activities.
    """
    logger.info("--- Starting up the application ---")
    
    # Ensure necessary directories exist
    # We use the paths defined in our centralized settings.
    temp_dir = Path(settings.TEMP_FILE_DIR)
    output_dir = Path(settings.OUTPUT_FILE_DIR)
    
    try:
        logger.info(f"Ensuring temporary directory exists: {temp_dir}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Ensuring output directory exists: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("All necessary directories are ready.")
    except Exception as e:
        logger.critical(f"FATAL: Could not create necessary directories. Error: {e}")
        # In a real production scenario, you might want the app to exit if it can't create dirs.
        # For now, we log a critical error.
        
    logger.info(f"Application '{settings.PROJECT_NAME}' startup complete.")


# --- Root Endpoint ---
# This is a simple health check endpoint to verify that the server is running.
@app.get("/", tags=["Health Check"])
def read_root():
    """
    A simple health check endpoint.
    Returns a welcome message indicating the API is operational.
    """
    return {"message": f"Welcome to {settings.PROJECT_NAME}. The API is running."}


# --- Placeholder for future API Routers ---
# In the next steps, we will create routers in the `api/` directory
# and include them here like this:
#
# from .api.v1.api import api_router
# app.include_router(api_router, prefix=settings.API_V1_STR)
# --- Include the API Router ---
# This is the crucial new line.
# It tells the main app to include all the routes defined in our api_router.
# The `prefix` ensures that all these routes will start with `/api/v1`.
app.include_router(api_router, prefix=settings.API_V1_STR)

# To run this application:
# uvicorn backend.app.main:app --reload
# To run this application:
# 1. Make sure you are in the project's root directory (doc_converter_pro).
# 2. Use the following command in your terminal:
#    uvicorn backend.app.main:app --reload