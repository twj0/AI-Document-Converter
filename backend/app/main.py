# backend/app/main.py (The Monolithic, Guaranteed Fix)

import logging
import shutil
from pathlib import Path
from uuid import uuid4, UUID
from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from celery import Celery
from celery.result import AsyncResult

# All necessary imports are now in this single file
from .core.config import settings
from .core.celery_app import celery_app
from .schemas.task import TaskCreated, TaskStatusResponse
from .tasks import non_ai_conversions, ai_conversions

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="A professional-grade API for converting documents using AI.",
    openapi_url="/api/v1/openapi.json"
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    logger.info("--- Starting up the application ---")
    Path(settings.TEMP_FILE_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.OUTPUT_FILE_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Application startup complete.")

# --- API Endpoints defined DIRECTLY on the app ---

@app.get("/", tags=["Health Check"])
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}."}

@app.post("/api/v1/tasks/upload", response_model=TaskCreated, status_code=202, tags=["Conversion Tasks"])
async def upload_and_dispatch_task(request: Request):
    """
    Accepts multipart/form-data, saves the file, and dispatches a background task.
    This version is registered directly on the main app to bypass router bugs.
    """
    try:
        form_data = await request.form()
        file = form_data.get("file")
        task_type = form_data.get("task_type")
        subject = form_data.get("subject", "General")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data.")

    if not file or not task_type:
        raise HTTPException(status_code=422, detail="Missing 'file' or 'task_type'.")

    request_id = uuid4()
    
    try:
        task_temp_dir = settings.TEMP_FILE_DIR / str(request_id)
        task_temp_dir.mkdir(parents=True, exist_ok=True)
        input_path = task_temp_dir / file.filename
        
        file_content = await file.read()
        with open(input_path, "wb") as buffer:
            buffer.write(file_content)
    finally:
        await file.close()

    output_dir = settings.OUTPUT_FILE_DIR / str(request_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    task_result: AsyncResult = None

    if task_type == "ppt_to_pdf":
        output_path = output_dir / f"{input_path.stem}.pdf"
        task_result = non_ai_conversions.ppt_to_pdf_task.delay(str(input_path), str(output_path))
    elif task_type in ["doc_to_markdown", "docx_to_markdown", "pdf_to_markdown"]:
        output_path = output_dir / f"{input_path.stem}.md"
        api_key = getattr(settings, f"{settings.AI_PROVIDER.upper()}_API_KEY", None)
        model_name = getattr(settings, f"{settings.AI_PROVIDER.upper()}_MODEL_NAME", None)
        if not api_key:
            raise HTTPException(status_code=400, detail=f"API Key for provider '{settings.AI_PROVIDER}' not set.")
        task_result = ai_conversions.ai_conversion_task.delay(str(input_path), str(output_path), subject, settings.AI_PROVIDER, api_key, model_name)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown task type: {task_type}")

    task_id = UUID(task_result.id)
    logger.info(f"Request [{request_id}]: Task dispatched with Celery ID [{task_id}]")
    return TaskCreated(id=task_id)


@app.get("/api/v1/tasks/status/{task_id}", response_model=TaskStatusResponse, tags=["Conversion Tasks"])
def get_task_status(task_id: UUID):
    """Polls for the status of a previously created Celery task."""
    task_result = AsyncResult(str(task_id), app=celery_app)
    status = task_result.status.lower()
    result = None

    if task_result.successful():
        status = "success"
        task_output = task_result.get()
        output_path = Path(task_output.get("output_path", ""))
        result = {
            "output_file_url": f"/downloads/{task_id}/{output_path.name}",
            "message": task_output.get("message"),
            "warnings": task_output.get("warnings", [])
        }
    elif task_result.failed():
        status = "failed"
        result = {"error_message": str(task_result.info)}
    elif status in ["pending", "started", "retry"]:
        status = "in_progress"
    
    return TaskStatusResponse(id=task_id, status=status, result=result)