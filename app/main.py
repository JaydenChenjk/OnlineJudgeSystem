from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from .auth import SessionMiddleware
from .routers import auth, users, problems, admin, languages, submissions, logs, import_export

app = FastAPI(title="Online Judge System", version="1.0.0")

# 添加Session中间件
app.add_middleware(SessionMiddleware)
    

@app.get("/")
async def welcome():
    return "Welcome!"


# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(problems.router)
app.include_router(admin.router)
app.include_router(languages.router)
app.include_router(submissions.router)
app.include_router(logs.router)
app.include_router(import_export.router)


# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "msg": str(exc.detail), "data": None}
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"code": 400, "msg": "参数错误", "data": None}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "服务器内部错误", "data": None}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # 启动服务器 