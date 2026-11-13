from typing import Dict, Any
import uuid

# 全局任务存储，生产环境建议换成redis
task_store: Dict[str, Dict[str, Any]] = {}

def create_task() -> str:
    task_id = f"task_{uuid.uuid4().hex}"
    task_store[task_id] = {
        "status": "pending",
        "result": None,
        "error": None
    }
    return task_id

def update_task(task_id: str, status: str, result=None, error=None):
    if task_id not in task_store:
        return
    task_store[task_id]["status"] = status
    if result is not None:
        task_store[task_id]["result"] = result
    if error is not None:
        task_store[task_id]["error"] = error

def get_task(task_id: str):
    return task_store.get(task_id)

def cancel_task(task_id: str):
    if task_id in task_store:
        task_store[task_id]["status"] = "canceled"
