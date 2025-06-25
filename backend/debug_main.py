# backend/app/debug_main.py (Final Corrected Imports)

import logging
import shutil
from pathlib import Path
from uuid import uuid4, UUID
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.cors import CORSMiddleware
from celery.result import AsyncResult

# --- THIS IS THE CRUCIAL FIX ---
# We use relative imports (starting with a dot) to tell Python to
# import from within the same package ('app'). This works correctly
# when the script is run from the project root.
from .core.config import settings
from .schemas.task import TaskCreated, TaskStatusResponse

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="DEBUG SERVER")

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    logger.info("--- Starting up DEBUG server ---")
    Path(settings.TEMP_FILE_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.OUTPUT_FILE_DIR).mkdir(parents=True, exist_ok=True)

# --- API Endpoints ---
@app.post("/api/v1/tasks/upload", response_model=TaskCreated, status_code=202)
async def upload_and_dispatch_task(request: Request):
    from .core.celery_app import celery_app
    
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
        
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        if file:
            await file.close()

    output_dir = settings.OUTPUT_FILE_DIR / str(request_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    task_name = ""
    task_args = []

    if task_type == "ppt_to_pdf":
        task_name = "tasks.ppt_to_pdf"
        output_path = output_dir / f"{input_path.stem}.pdf"
        task_args = [str(input_path), str(output_path)]
    elif task_type in ["doc_to_markdown", "docx_to_markdown", "pdf_to_markdown"]:
        task_name = "tasks.ai_conversion"
        output_path = output_dir / f"{input_path.stem}.md"
        api_key = getattr(settings, f"{settings.AI_PROVIDER.upper()}_API_KEY", None)
        model_name = getattr(settings, f"{settings.AI_PROVIDER.upper()}_MODEL_NAME", None)
        if not api_key:
            raise HTTPException(status_code=400, detail="API Key not set.")
        task_args = [str(input_path), str(output_path), subject, settings.AI_PROVIDER, api_key, model_name]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown task type: {task_type}")

    task_result = celery_app.send_task(task_name, args=task_args)
    return TaskCreated(id=UUID(task_result.id))


@app.get("/api/v1/tasks/status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: UUID):
    from .core.celery_app import celery_app
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