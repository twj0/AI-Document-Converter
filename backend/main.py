# backend/main.py (Final, Corrected Absolute Import)
import logging
import shutil
from pathlib import Path
from uuid import uuid4, UUID
from fastapi import FastAPI, Request, HTTPException, Path as FastApiPath
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from celery import Celery
from celery.result import AsyncResult

# --- THIS IS THE CRUCIAL FIX ---
# We now import `dotenv_values` directly from the third-party library `dotenv`,
# NOT using a relative path.
from dotenv import dotenv_values
from .schemas.task import TaskCreated, TaskStatusResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WEB] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

config = dotenv_values(".env")
TEMP_DIR = Path("temp_files")
OUTPUT_DIR = Path("output_files")

app = FastAPI(title="AI Document Converter API")
celery_producer = Celery('producer', broker="redis://127.0.0.1:6379/0", backend="redis://127.0.0.1:6379/0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/v1/tasks/upload", response_model=TaskCreated, status_code=202)
async def upload_and_dispatch(request: Request):
    form = await request.form()
    file = form.get("file")
    task_type = form.get("task_type")
    
    if not file or not task_type:
        raise HTTPException(422, "Missing 'file' or 'task_type'.")

    req_id = uuid4()
    input_path = TEMP_DIR / str(req_id) / file.filename
    input_path.parent.mkdir()
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    await file.close()

    output_path_base = OUTPUT_DIR / str(req_id)
    output_path_base.mkdir()
    
    task_name, args = "", []
    provider_name = config.get("AI_PROVIDER", "gemini")

    if task_type == "ppt_to_pdf":
        task_name, args = "tasks.ppt_to_pdf", [str(input_path), str(output_path_base / f"{input_path.stem}.pdf")]
    
    elif task_type in ["doc_to_markdown", "docx_to_markdown", "pdf_to_markdown"]:
        api_key = config.get(f"{provider_name.upper()}_API_KEY")
        model_name = config.get(f"{provider_name.upper()}_MODEL_NAME")
        if not api_key or not model_name: raise HTTPException(400, "AI Provider not configured in .env")
        task_name, args = "tasks.ai_conversion", [str(input_path), str(output_path_base / f"{input_path.stem}.md"), form.get("subject", "General"), provider_name, api_key, model_name]
    
    else:
        raise HTTPException(400, "Unknown task type.")

    task_result = celery_producer.send_task(task_name, args=args)
    return TaskCreated(id=task_result.id)


@app.get("/api/v1/tasks/status/{task_id}", response_model=TaskStatusResponse)
def get_status(task_id: UUID):
    task = AsyncResult(str(task_id), app=celery_producer)
    res = {"id": task_id, "status": task.status, "result": None}
    if task.successful():
        res["status"] = "success"
        res["result"] = task.result
        if res["result"] and 'output_path' in res["result"]:
            p_out = Path(res['result']['output_path'])
            res['result']['output_file_url'] = f"/api/v1/downloads/{p_out.parent.name}/{p_out.name}"
    elif task.failed():
        res["status"] = "failed"
        res["result"] = {"error_message": str(task.info)}
    return res


@app.get("/api/v1/downloads/{request_id}/{file_name}")
def download_file(request_id: str, file_name: str):
    file_path = OUTPUT_DIR / request_id / file_name
    if file_path.is_file():
        return FileResponse(file_path, media_type='application/octet-stream', filename=file_name)
    raise HTTPException(status_code=404, detail="File not found.")