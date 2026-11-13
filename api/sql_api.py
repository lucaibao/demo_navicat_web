import os
import logging
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

# 内存任务池
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

    # 端口转换
    try:
        real_port = int(real_port_str) if real_port_str else 3306
    except ValueError:
        logger.warning(f"端口解析失败，输入值：{real_port_str}，默认使用3306")
        real_port = 3306

    logger.info("===== 收到SQL执行请求 =====")
    logger.info(f"数据库类型: {req.db_type}")
    logger.info(f"连接信息 -> host={real_host}, port={real_port}, user={real_user}, database={real_db}, schema={real_schema}")
    logger.info(f"timeout_sec: {req.timeout_sec}, max_rows: {req.max_rows}")
    logger.info(f"confirm_risk: {req.confirm_risk}")
    logger.info(f"待执行SQL:\n{req.sql}")

    task_id = str(uuid.uuid4())
    # 存入db_type，子线程判断使用
    task_map[task_id] = {
        "status": "running",
        "sql": req.sql,
        "db_type": req.db_type,
        "real_host": real_host,
        "real_port": real_port,
        "real_user": real_user,
        "real_pwd": real_pwd,
        "real_db": real_db,
        "real_schema": real_schema,
        "result": None,
        "error": None
    }

    def run_sql_task():
        task = task_map[task_id]
        sql = task["sql"]
        db_type = task["db_type"]
        h = task["real_host"]
        p = task["real_port"]
        u = task["real_user"]
        pw = task["real_pwd"]
        db = task["real_db"]

        try:
            if db_type in ("mysql", "gaussdb"):
                # mysql / GaussDB M模式，使用pymysql
                import pymysql
                conn = pymysql.connect(
                    host=h,
                    port=p,
                    user=u,
                    password=pw,
                    database=db,
                    charset="utf8mb4"
                )
                try:
                    cur = conn.cursor()
                    cur.execute(sql)
                    if cur.description:
                        # 查询语句，返回列+行
                        columns = [col[0] for col in cur.description]
                        rows = cur.fetchall()
                        task["result"] = {"columns": columns, "rows": rows}
                    else:
                        # DML语句
                        task["result"] = {"msg": f"执行成功，影响行数：{cur.rowcount}"}
                    conn.commit()
                    logger.info(f"task_id={task_id}, 输出结果：{task}")
                finally:
                    cur.close()
                    conn.close()

            # ========== GaussDB PG原生模式 暂时注释，后续需要再放开 ==========
            # elif db_type == "gaussdb_pg":
            #     import psycopg2
            #     import psycopg2.extras
            #     conn_params = {
            #         "host": h,
            #         "port": p,
            #         "user": u,
            #         "password": pw,
            #         "dbname": db
            #     }
            #     if task["real_schema"]:
            #         conn_params["options"] = f"-c search_path={task['real_schema']}"
            #     with psycopg2.connect(**conn_params) as pg_conn:
            #         with pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            #             cur.execute(sql)
            #             if cur.description:
            #                 columns = [col.name for col in cur.description]
            #                 rows = []
            #                 for row in cur.fetchall():
            #                     row_data = [row[c] for c in columns]
            #                     rows.append(row_data)
            #                 task["result"] = {"columns": columns, "rows": rows}
            #             else:
            #                 task["result"] = {"msg": f"执行成功，影响行数：{cur.rowcount}"}
            # =================================================================

            task["status"] = "finished"
            logger.info(f"task {task_id} 执行完成")
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            logger.error(f"task {task_id} 执行异常：{e}", exc_info=True)

    t = threading.Thread(target=run_sql_task, daemon=True)
    t.start()
    logger.info(f"任务创建成功，task_id={task_id}")
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
    logger.info(f"取消任务 task_id={task_id}")
    task = task_map.get(task_id)
    if task:
        task["status"] = "canceled"
    return {"msg": "cancel ok"}
