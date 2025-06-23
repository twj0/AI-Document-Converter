# backend/app/schemas/task.py

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from uuid import UUID, uuid4

# --- Task Status Enum ---
# Using a Literal type is a good way to enforce specific string values.
TaskStatus = Literal["pending", "in_progress", "success", "failed"]

# --- Base Task Schema ---
class TaskBase(BaseModel):
    """Base model for task properties."""
    # The `Field` function allows us to add metadata, like a default factory.
    # `default_factory=uuid4` ensures that every new task gets a unique ID.
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the task")

# --- Schema for Task Creation Response ---
class TaskCreated(TaskBase):
    """
    Schema for the response sent back immediately after a task is created.
    This confirms to the client that the task has been accepted.
    """
    message: str = "Task accepted and is being processed."


# --- Schema for Detailed Task Status ---
class TaskStatusResponse(TaskBase):
    """
    Schema for the response when a client polls for the status of a task.
    """
    status: TaskStatus = Field("pending", description="The current status of the task")
    # `result` can be anything (e.g., a path to a file, an error message),
    # so we use the `Any` type.
    result: Optional[Any] = Field(None, description="The result of the task (e.g., file URL, error message)")


# --- Schema for Conversion Task Specifics (for more complex scenarios) ---
# While not used in the initial simple API, this demonstrates how you could
# structure more complex responses.
class ConversionResult(BaseModel):
    """A more structured result for a successful conversion."""
    output_file_url: str = Field(..., description="URL to download the converted file")
    source_filename: str
    warnings: Optional[List[str]] = None

class FailedConversionResult(BaseModel):
    """A structured result for a failed conversion."""
    error_message: str
    source_filename: str

# --- Main Block for Testing ---
if __name__ == '__main__':
    # You can run this file directly to see examples of the schemas in action.
    print("--- Testing Task Schemas ---")

    # 1. Create a TaskCreated response
    created_response = TaskCreated()
    print("\n[Example] TaskCreated Response:")
    # .model_dump_json() is the Pydantic v2 way to serialize to JSON
    print(created_response.model_dump_json(indent=2))
    # Note that a new random UUID is generated each time.

    # 2. Create a TaskStatusResponse for a successful task
    successful_status = TaskStatusResponse(
        id=created_response.id,
        status="success",
        result={
            "output_file_url": "/downloads/mydocument.pdf",
            "source_filename": "original.ppt",
            "warnings": ["A font was substituted on page 3."]
        }
    )
    print("\n[Example] Successful TaskStatusResponse:")
    print(successful_status.model_dump_json(indent=2))

    # 3. Create a TaskStatusResponse for a failed task
    failed_status = TaskStatusResponse(
        id=created_response.id,
        status="failed",
        result={
            "error_message": "Microsoft Office is not installed or the file is corrupt.",
            "source_filename": "broken.doc"
        }
    )
    print("\n[Example] Failed TaskStatusResponse:")
    print(failed_status.model_dump_json(indent=2))

    print("\n--- Schema Tests Complete ---")