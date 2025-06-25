# backend/worker.py (Final Corrected Imports)
import logging
from celery import Celery
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WORKER] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

celery_worker = Celery(
    'tasks',
    broker="redis://127.0.0.1:6379/0",
    backend="redis://127.0.0.1:6379/0"
)

@celery_worker.task(name="tasks.ppt_to_pdf")
def ppt_to_pdf_task(input_path_str: str, output_path_str: str) -> dict:
    logger.info(f"Received ppt_to_pdf_task for: {input_path_str}")
    # --- THIS IS THE CRUCIAL FIX ---
    from .services import file_processor # Use relative import
    try:
        file_processor.convert_to_pdf_com(input_path_str, output_path_str)
        return {"status": "success", "message": "File converted to PDF successfully.", "output_path": output_path_str}
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise e

@celery_worker.task(name="tasks.ai_conversion")
def ai_conversion_task(input_path_str, output_path_str, subject, provider_name, api_key, model_name) -> dict:
    logger.info(f"Received ai_conversion_task for: {input_path_str}")
    # --- THIS IS THE CRUCIAL FIX ---
    from .services import file_processor, ai_service # Use relative import
    try:
        text_content = file_processor.extract_text_smart(input_path_str)
        if not text_content: raise ValueError("Extracted text is empty.")
        ai_provider = ai_service.get_ai_provider(provider_name, model_name, api_key)
        structured_result = ai_provider.generate_structured_markdown(text_content, subject, Path(input_path_str).suffix)
        markdown_content = structured_result.get("markdown_content", "")
        if not markdown_content: raise ValueError("AI did not return any markdown content.")
        with open(output_path_str, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return {"status": "success", "message": "AI conversion successful.", "output_path": output_path_str, "warnings": structured_result.get("warnings", [])}
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise e