# backend/schemas/task.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Literal
from uuid import UUID, uuid4

# 使用 Literal 类型来严格限定任务状态的字符串值，非常稳健。
TaskStatus = Literal["pending", "in_progress", "success", "failed"]

class TaskCreated(BaseModel):
    """
    当任务被成功派发后，API 立即返回的响应模型。
    """
    id: UUID = Field(..., description="由 Celery 生成的唯一任务 ID")


class TaskStatusResult(BaseModel):
    """
    代表一个成功或失败任务的详细结果。
    """
    # 成功时的字段
    output_file_url: Optional[str] = Field(None, description="成功转换后的文件下载链接")
    message: Optional[str] = Field(None, description="任务成功或失败的摘要信息")
    warnings: Optional[List[str]] = Field(None, description="AI 转换过程中可能产生的警告")
    # 失败时的字段
    error_message: Optional[str] = Field(None, description="任务失败时的详细错误信息")


class TaskStatusResponse(BaseModel):
    """
    用于查询任务状态的 API 响应模型。
    """
    id: UUID = Field(..., description="被查询的任务 ID")
    status: TaskStatus = Field(..., description="任务的当前状态")
    result: Optional[TaskStatusResult] = Field(None, description="任务的最终结果，仅在任务完成时出现")


# --- 用于独立测试的代码块 ---
if __name__ == '__main__':
    # 你可以运行 python backend/schemas/task.py 来测试这个文件
    print("--- 正在测试 Task Schemas ---")

    task_id = uuid4()

    # 1. 模拟一个成功任务的响应
    success_response = TaskStatusResponse(
        id=task_id,
        status="success",
        result=TaskStatusResult(
            output_file_url=f"/downloads/{task_id}/mydoc.md",
            message="File converted successfully.",
            warnings=["A font was substituted."]
        )
    )
    print("\n[示例] 成功任务的状态响应:")
    print(success_response.model_dump_json(indent=2))

    # 2. 模拟一个失败任务的响应
    failed_response = TaskStatusResponse(
        id=task_id,
        status="failed",
        result=TaskStatusResult(
            error_message="Microsoft Office not installed."
        )
    )
    print("\n[示例] 失败任务的状态响应:")
    print(failed_response.model_dump_json(indent=2))

    # 3. 模拟一个正在进行中的任务的响应
    in_progress_response = TaskStatusResponse(
        id=task_id,
        status="in_progress"
    )
    print("\n[示例] 进行中任务的状态响应:")
    print(in_progress_response.model_dump_json(indent=2))