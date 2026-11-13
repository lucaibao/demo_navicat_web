# SQL在线查询工具

基于 FastAPI + 异步数据库驱动 实现的内网 SQL 执行面板，支持 MySQL、PostgreSQL。
采用异步任务后台执行，前端轮询获取结果，支持批量SQL、高危SQL二次确认、任务取消、结果表格渲染。

> ⚠️ 重要提示：**仅限内网运维、审计场景使用，严禁直接暴露到公网**

## ✨ 功能特性
- ✅ 支持选中片段执行 / 整段SQL执行，自动按分号切分批量SQL顺序执行
- ✅ 异步任务模型，后端后台执行，前端轮询任务状态，支持取消正在执行的任务
- ✅ 内置高危SQL拦截，检测到高危语句时弹出确认弹窗，防止误操作
- ✅ 两种连接配置方式：预定义环境变量（DB_前缀）选择 或 手动填写连接信息
- ✅ 界面交互：配置面板折叠、左右拖拽分割线、全屏模式
- ✅ 结果自动渲染表格，时间字段自动格式化（将 `T` 替换为空格）
- ✅ 展示查询总行数、结果截断标记、DML影响行数
- ✅ 右侧结果面板一键清空
- ✅ 支持自定义最大返回行数、SQL执行超时时间

## 🧩 技术栈
### 后端
- Python 3.10+
- FastAPI：Web框架
- uvicorn：ASGI服务
- aiomysql：MySQL异步驱动
- PyMySQL：MySQL同步驱动
- asyncpg：PostgreSQL异步驱动
- pydantic v2：参数校验
- python-dotenv：环境变量加载
- opentelemetry-api：链路追踪
- click：命令行工具

### 前端
- 原生 HTML + JavaScript + CSS，无第三方前端框架
- 内置拖拽分割、全屏、折叠面板交互

## 📦 依赖清单
`requirements.txt`
```txt
fastapi==0.162.5
uvicorn==0.54.0
aiomysql==0.3.2
asyncpg==0.32.0
PyMySQL==1.2.4
python-dotenv==1.2.4
python-multipart==0.0.33
pydantic==2.14.3
opentelemetry-api==1.45.2
click==8.5.1
