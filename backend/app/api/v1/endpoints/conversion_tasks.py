# backend/app/api/v1/endpoints/conversion_tasks.py

import logging
import shutil
from pathlib import Path
from uuid import UUID  # <--- FIXED: Import UUID here
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Form,
)

from ....core.config import settings
from ....schemas.task import TaskCreated, TaskStatusResponse
from ....services import file_processor, ai_service

logger = logging.getLogger(__name__)

router = APIRouter()

tasks_db = {}


@router.post("/upload", response_model=TaskCreated, status_code=202)
def upload_and_convert_file(
    task_type: str = Form(..., description="Type of conversion task. E.g., 'ppt_to_pdf', 'doc_to_markdown'."),
    subject: str = Form("General", description="Subject for AI-based conversions."),
    file: UploadFile = File(...)
):
    task = TaskCreated()
    task_id = task.id

    try:
        task_temp_dir = settings.TEMP_FILE_DIR / str(task_id)
        task_temp_dir.mkdir(parents=True, exist_ok=True)
        input_path = task_temp_dir / file.filename

        logger.info(f"Task [{task_id}]: Saving uploaded file to {input_path}")
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Task [{task_id}]: Failed to save uploaded file. Error: {e}")
        raise HTTPException(status_code=500, detail="Could not save file.")
    finally:
        file.file.close()

    tasks_db[task_id] = TaskStatusResponse(id=task_id, status="in_progress")
    logger.info(f"Task [{task_id}]: Set status to 'in_progress'.")

    try:
        logger.info(f"Task [{task_id}]: Executing synchronous task: {task_type}")
        output_file_path = None
        structured_result = {} # Initialize for potential later use

        if task_type == "ppt_to_pdf":
            output_dir = settings.OUTPUT_FILE_DIR / str(task_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file_path = output_dir / f"{input_path.stem}.pdf"
            file_processor.convert_to_pdf_com(input_path, output_file_path)

        elif task_type in ["doc_to_markdown", "docx_to_markdown", "pdf_to_markdown"]:
            output_dir = settings.OUTPUT_FILE_DIR / str(task_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file_path = output_dir / f"{input_path.stem}.md"

            text = ""
            if input_path.suffix.lower() == ".doc":
                text = file_processor.extract_text_from_doc(input_path)
            elif input_path.suffix.lower() == ".docx":
                text = file_processor.extract_text_from_docx(input_path)
            elif input_path.suffix.lower() == ".pdf":
                text = file_processor.extract_text_from_pdf(input_path)
            else:
                raise ValueError(f"Unsupported file type for this task: {input_path.suffix}")

            if not text.strip():
                 raise ValueError("Extracted text is empty, cannot proceed with AI conversion.")

            # You MUST have your chosen provider's API key set in .env for this to work.
            api_key = getattr(settings, f"{settings.AI_PROVIDER.upper()}_API_KEY", None)
            model_name = getattr(settings, f"{settings.AI_PROVIDER.upper()}_MODEL_NAME", None)

            if not api_key:
                raise ValueError(f"API Key for provider '{settings.AI_PROVIDER}' is not configured.")

            ai_provider = ai_service.get_ai_provider(
                provider_name=settings.AI_PROVIDER,
                model_name=model_name,
                api_key=api_key
            )
            structured_result = ai_provider.generate_structured_markdown(
                text_content=text,
                subject=subject,
                file_type=input_path.suffix.upper()
            )
            markdown_content = structured_result.get("markdown_content", "")
            
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

        success_result = {
            "output_file_url": f"/downloads/{task_id}/{output_file_path.name}",
            "source_filename": file.filename,
            "warnings": structured_result.get("warnings", [])
        }
        tasks_db[task_id] = TaskStatusResponse(id=task_id, status="success", result=success_result)
        logger.info(f"Task [{task_id}]: Task completed successfully.")

    except Exception as e:
        logger.error(f"Task [{task_id}]: An error occurred during processing. Error: {e}", exc_info=True)
        tasks_db[task_id] = TaskStatusResponse(
            id=task_id,
            status="failed",
            result={"error_message": str(e), "source_filename": file.filename}
        )

    return task


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: UUID): # Use UUID directly here for automatic validation
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task