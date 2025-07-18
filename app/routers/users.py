from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional
from ..models import UserCreate, UserRoleUpdate, data_store
from ..auth import require_auth, require_admin, get_current_user, login_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", summary="用户注册")
async def register_user(user_data: UserCreate):
    """用户注册"""
    try:
        user_id = data_store.create_user(user_data.username, user_data.password)
        return {"code": 200, "msg": "register success", "data": {"user_id": user_id}}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "msg": str(e)}
        )


@router.get("/", summary="获取用户列表")
async def get_users_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    request: Request = None
):   # 获取用户列表（仅管理员）
    require_admin(request)  
    
    try:
        result = data_store.get_all_users(page, page_size)
        
        # 转换用户信息格式
        users = []
        for user in result["users"]:
            users.append({
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user["role"],
                "join_time": user["join_time"],
                "submit_count": user["submit_count"],
                "resolve_count": user["resolve_count"]
            })
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "total": result["total"],
                "users": users
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取用户列表失败: {str(e)}"}
        )


@router.get("/{user_id}", summary="获取用户信息")
async def get_user_info(user_id: str, request: Request):   # 获取用户信息
    current_user = get_current_user(request)
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "msg": "未登录"}
        )
    
    if current_user["user_id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "msg": "权限不足"}
        )
    
    user = data_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "msg": "用户不存在"}
        )
    
    # 返回用户信息（不包含密码）
    user_info = {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "join_time": user["join_time"],
        "submit_count": user["submit_count"],
        "resolve_count": user["resolve_count"]
    }
    
    return {"code": 200, "msg": "success", "data": user_info}


@router.put("/{user_id}/role", summary="更新用户角色")
async def update_user_role(user_id: str, role_data: UserRoleUpdate, request: Request):   # 更新用户角色（仅管理员）
    require_admin(request)  
    
    # 检查用户是否存在
    user = data_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "msg": "用户不存在"}
        )
    
    try:
        data_store.update_user_role(user_id, role_data.role)
        return {"code": 200, "msg": "role updated", "data": {"user_id": user_id, "role": role_data.role}}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "msg": str(e)}
        )


@router.post("/admin", summary="创建管理员账户")
async def create_admin(user_data: UserCreate, request: Request):   # 创建管理员账户（仅管理员）
    require_admin(request)  
    
    try:
        user_id = data_store.create_user(user_data.username, user_data.password, "admin")
        return {"code": 200, "msg": "success", "data": {"user_id": user_id, "username": user_data.username}}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "msg": str(e)}
        ) 