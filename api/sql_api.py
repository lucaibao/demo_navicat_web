import os
import logging
import time
import uuid
import threading
from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("sql-console")

task_map: Dict[str, Dict[str, Any]] = {}

class SqlRunRequest(BaseModel):
    db_type: str
    host_key: Optional[str] = ""
    host: Optional[str] = ""

    port_key: Optional[str] = ""
    port: Optional[str] = ""

    user_key: Optional[str] = ""
    user: Optional[str] = ""

    pwd_key: Optional[str] = ""
    password: Optional[str] = ""

    dbname_key: Optional[str] = ""
    database: Optional[str] = ""

    schema_key: Optional[str] = ""
    db_schema: Optional[str] = ""

    sql: str
    timeout_sec: Optional[int] = None
    max_rows: Optional[int] = None
    confirm_risk: bool = False


def get_env_or_input(env_key: str, input_val: str) -> str:
    if env_key and env_key in os.environ:
        return os.environ[env_key]
    return input_val.strip() if input_val else ""


@router.post("/api/sql/run")
async def sql_run(req: SqlRunRequest):
    real_host = get_env_or_input(req.host_key, req.host)
    real_port_str = get_env_or_input(req.port_key, req.port)
    real_user = get_env_or_input(req.user_key, req.user)
    real_pwd = get_env_or_input(req.pwd_key, req.password)
    real_db = get_env_or_input(req.dbname_key, req.database)
    real_schema = get_env_or_input(req.schema_key, req.db_schema)

    try:
        real_port = int(real_port_str) if real_port_str else 3306
    except ValueError:
        logger.warning(f"端口解析失败，收到值：{real_port_str}，使用默认3306")
        real_port = 3306

    logger.info("===== 收到SQL执行请求 =====")
    logger.info(f"数据库类型: {req.db_type}")
    logger.info(f"连接信息 -> host={real_host}, port={real_port}, user={real_user}, database={real_db}, schema={real_schema}")
    logger.info(f"timeout_sec: {req.timeout_sec}, max_rows: {req.max_rows}")
    logger.info(f"confirm_risk: {req.confirm_risk}")
    logger.info(f"待执行SQL:\n{req.sql}")

    task_id = str(uuid.uuid4())
    task_map[task_id] = {
        "status": "running",
        "sql": req.sql,
        "result": None,
        "error": None
    }

    def run_sql_task():
        try:
            # --------------------------
            # 这里后续替换成真实数据库执行代码
            time.sleep(1.2)
            task_map[task_id]["status"] = "finished"
            task_map[task_id]["result"] = {"columns": ["?column?"], "rows": [[1]]}
            logger.info(f"task {task_id} 执行完成")
        except Exception as e:
            task_map[task_id]["status"] = "failed"
            task_map[task_id]["error"] = str(e)
            logger.error(f"task {task_id} 执行异常：{e}")

    t = threading.Thread(target=run_sql_task, daemon=True)
    t.start()
    logger.info(f"SQL任务创建成功，task_id={task_id}")
    return {"task_id": task_id}


@router.get("/api/sql/status/{task_id}")
async def get_task_status(task_id: str):
    logger.info(f"查询任务状态 task_id={task_id}")
    task = task_map.get(task_id)
    if not task:
        return {"status": "not_found", "result": None, "error": "任务不存在"}
    return {
        "status": task["status"],
        "result": task["result"],
        "error": task["error"]
    }


@router.post("/api/sql/cancel/{task_id}")
async def cancel_task(task_id: str):
    logger.info(f"请求取消任务 task_id={task_id}")
    task = task_map.get(task_id)
    if task:
        task["status"] = "canceled"
    return {"msg": "cancel ok"}
