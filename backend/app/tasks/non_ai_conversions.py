# backend/app/tasks/non_ai_conversions.py

import logging
from pathlib import Path

# Import the main celery app instance we created
from ..core.celery_app import celery_app
# Import our core file processing logic
from ..services import file_processor

# --- Configure Logging ---
logger = logging.getLogger(__name__)

# --- Celery Task Definition ---

# The `@celery_app.task` decorator registers this function as a Celery task.
# `bind=True` allows us to access task metadata (like its own ID) via `self`.
# `name='tasks.ppt_to_pdf'` gives the task an explicit name, which is good practice.
@celery_app.task(bind=True, name="tasks.ppt_to_pdf")
def ppt_to_pdf_task(self, input_path_str: str, output_path_str: str) -> dict:
    """
    A Celery task to convert a PowerPoint file to PDF.

    Args:
        self: The task instance (automatically injected by `bind=True`).
        input_path_str: The string path to the source PowerPoint file.
        output_path_str: The string path where the output PDF should be saved.

    Returns:
        A dictionary containing the result of the operation.
    """
    task_id = self.request.id
    logger.info(f"Task [{task_id}]: Starting PPT to PDF conversion.")
    logger.info(f"Task [{task_id}]: Input: {input_path_str}, Output: {output_path_str}")

    try:
        # Convert string paths back to Path objects
        input_path = Path(input_path_str)
        output_path = Path(output_path_str)

        # --- Call the core service logic ---
        # The task's responsibility is to orchestrate, not to contain business logic.
        file_processor.convert_to_pdf_com(input_path, output_path)

        # If the service call completes without error, the task is successful.
        result = {
            "status": "success",
            "message": "File converted successfully.",
            "output_path": str(output_path)
        }
        logger.info(f"Task [{task_id}]: Conversion successful.")
        return result

    except Exception as e:
        # If any exception occurs in the service, the task has failed.
        logger.error(f"Task [{task_id}]: Conversion failed. Reason: {e}", exc_info=True)
        result = {
            "status": "failed",
            "message": f"An error occurred: {e}"
        }
        # It's good practice to re-raise the exception so Celery's monitoring
        # tools can properly register the task as 'FAILED'.
        # self.update_state(state='FAILURE', meta=result)
        # raise e
        # For simplicity in our API, we'll just return the failure dict.
        return result


# You can add more non-AI conversion tasks here in the future.
# For example, a task to convert Word to PDF would be very similar.
#
# @celery_app.task(bind=True, name="tasks.word_to_pdf")
# def word_to_pdf_task(self, input_path_str: str, output_path_str: str) -> dict:
#     # ... implementation similar to the above ...
#     pass