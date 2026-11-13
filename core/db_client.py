import pymysql
from datetime import datetime
from typing import Optional, Dict, Any


def is_risk_sql(sql: str) -> bool:
    s = sql.strip().lower()
    risk_keywords = ["drop", "truncate", "alter", "delete", "update"]
    for kw in risk_keywords:
        if kw in s:
            return True
    return False


def exec_sql(
    db_type: str,
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    schema: str,
    sql: str,
    timeout: int,
    max_rows: int
) -> Dict[str, Any]:
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=timeout
        )
        # GaussDB M兼容模式切换schema
        if schema and schema.strip():
            sc = conn.cursor()
            sc.execute(f"SET SCHEMA {schema.strip()};")
            sc.close()

        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.description:
            # 查询语句
            columns = [col[0] for col in cursor.description]
            all_rows = cursor.fetchall()
            truncated = len(all_rows) > max_rows
            rows = all_rows[:max_rows]
            out_rows = []
            for row in rows:
                line = []
                for cell in row:
                    if isinstance(cell, datetime):
                        line.append(cell.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        line.append(cell)
                out_rows.append(line)
            return {
                "columns": columns,
                "rows": out_rows,
                "row_count": len(all_rows),
                "truncated": truncated
            }
        else:
            # DML
            conn.commit()
            return {"affected_rows": cursor.rowcount}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
