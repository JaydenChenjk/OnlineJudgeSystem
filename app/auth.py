from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from .models import data_store


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 从Cookie中获取session_id
        session_id = request.cookies.get("session_id")
        
        if session_id:
            session = data_store.get_session(session_id)
            if session:
                user = data_store.get_user_by_id(session["user_id"])
                if user:
                    request.state.user = user
                    request.state.session_id = session_id
        
        response = await call_next(request)
        
        # 如果响应中设置了新的session_id，添加到Cookie
        if hasattr(request.state, 'new_session_id'):
            response.set_cookie(
                key="session_id",
                value=request.state.new_session_id,
                httponly=True,
                max_age=3600 * 24 * 7  # 7天过期
            )
        
        return response


def require_auth(request: Request):     # 要求用户已登录
    if not hasattr(request.state, 'user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "msg": "未登录"}
        )
    return request.state.user


def require_admin(request: Request):    # 要求用户是管理员
    user = require_auth(request)
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "msg": "权限不足"}
        )
    return user


def get_current_user(request: Request):     # 获取当前用户（可选）
    return getattr(request.state, 'user', None)


def login_user(request: Request, user_id: str):     # 登录用户
    session_id = data_store.create_session(user_id)
    request.state.new_session_id = session_id


def logout_user(request: Request):      #登出用户
    if hasattr(request.state, 'session_id'):
        data_store.delete_session(request.state.session_id)
        # 清除Cookie
        response = Response()
        response.delete_cookie("session_id")
        return response
    return None 