from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
from api.sql_api import router as sql_router

load_dotenv()

app = FastAPI(title="GaussDB Web SQL Console")

# 挂载静态目录
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(sql_router)

# 【修正后的接口：返回DB_开头变量名列表，供下拉选择】
@app.get("/api/db-env")
def get_db_env():
    db_keys = [k for k in os.environ.keys() if k.startswith("DB_")]
    return {"db_keys": db_keys}

# 首页路由
@app.get("/")
async def index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVER_PORT", 18888))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
