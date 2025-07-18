from fastapi import APIRouter, Request, HTTPException, status, Response
from ..models import UserLogin, data_store
from ..auth import login_user, logout_user, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", summary="用户登录")
async def login(request: Request, login_data: UserLogin):   # 用户登录
    user = data_store.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "msg": "用户名或密码错误"}
        )
    
    # 登录用户
    login_user(request, user["user_id"])
    
    return {
        "code": 200,
        "msg": "login success",
        "data": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        }
    }


@router.post("/logout", summary="用户登出")
async def logout(request: Request):   # 用户登出
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "msg": "未登录"}
        )
    
    # 删除session
    if hasattr(request.state, 'session_id'):
        data_store.delete_session(request.state.session_id)
    
    # 创建响应并清除Cookie
    response = Response(content='{"code": 200, "msg": "logout success", "data": null}')
    response.headers["content-type"] = "application/json"
    response.delete_cookie("session_id")
    
    return response 