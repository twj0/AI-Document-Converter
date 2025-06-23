# backend/app/tasks/ai_conversions.py

import logging
from pathlib import Path

# Import the main celery app instance
from ..core.celery_app import celery_app
# Import our core service logic
from ..services import file_processor, ai_service
# Import settings to get default provider info if needed
from ..core.config import settings

# --- Configure Logging ---
logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.ai_conversion")
def ai_conversion_task(self,
                       input_path_str: str,
                       output_path_str: str,
                       subject: str,
                       api_key: str, # Pass the key directly to the task
                       provider_name: str = settings.AI_PROVIDER,
                       model_name: str = None) -> dict:
    """
    A Celery task to perform AI-based file conversions (e.g., DOC to Markdown).

    Args:
        self: The task instance.
        input_path_str: String path to the source document.
        output_path_str: String path for the output Markdown file.
        subject: The subject of the document for the AI prompt.
        api_key: The API key for the selected provider.
        provider_name: The name of the AI provider to use.
        model_name: The specific model name to use.

    Returns:
        A dictionary containing the result of the operation.
    """
    task_id = self.request.id
    logger.info(f"Task [{task_id}]: Starting AI conversion.")
    logger.info(f"Task [{task_id}]: Input: {input_path_str}, Output: {output_path_str}")

    try:
        input_path = Path(input_path_str)
        output_path = Path(output_path_str)

        # --- Step 1: Extract Text ---
        logger.info(f"Task [{task_id}]: Extracting text from '{input_path.name}'...")
        text_content = ""
        file_suffix = input_path.suffix.lower()

        if file_suffix == '.doc':
            text_content = file_processor.extract_text_from_doc(input_path)
        elif file_suffix == '.docx':
            text_content = file_processor.extract_text_from_docx(input_path)
        elif file_suffix == '.pdf':
            text_content = file_processor.extract_text_from_pdf(input_path)
        else:
            raise ValueError(f"Unsupported file type for AI conversion: {file_suffix}")

        if not text_content or not text_content.strip():
            raise ValueError("Extracted text is empty. Cannot proceed with AI conversion.")
        
        logger.info(f"Task [{task_id}]: Text extraction successful (length: {len(text_content)}).")

        # --- Step 2: Call AI Service ---
        logger.info(f"Task [{task_id}]: Calling AI provider '{provider_name}'...")
        
        # Determine model name to use
        if not model_name:
            model_name = getattr(settings, f"{provider_name.upper()}_MODEL_NAME", None)
            if not model_name:
                 raise ValueError(f"No default model name configured for provider '{provider_name}'.")

        ai_provider = ai_service.get_ai_provider(
            provider_name=provider_name,
            model_name=model_name,
            api_key=api_key
        )
        
        structured_result = ai_provider.generate_structured_markdown(
            text_content=text_content,
            subject=subject,
            file_type=file_suffix.upper()
        )
        logger.info(f"Task [{task_id}]: AI processing successful.")

        # --- Step 3: Save Output ---
        markdown_content = structured_result.get("markdown_content")
        if not markdown_content:
            raise ValueError("AI returned an empty markdown content.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        logger.info(f"Task [{task_id}]: Markdown file saved to '{output_path}'.")

        # --- Step 4: Prepare and Return Result ---
        final_result = {
            "status": "success",
            "message": "File converted successfully using AI.",
            "output_path": str(output_path),
            "warnings": structured_result.get("warnings", [])
        }
        return final_result

    except Exception as e:
        logger.error(f"Task [{task_id}]: AI conversion failed. Reason: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"An error occurred during AI conversion: {e}"
        }