from fastapi import APIRouter, Request
from ..models import data_store
from ..auth import require_admin

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/reset/", summary="重置系统")
async def reset_system(request: Request):
    """重置系统（仅管理员）"""
    require_admin(request)  # 检查管理员权限
    
    data_store.reset_system()
    
    return {"code": 200, "msg": "system reset successfully", "data": None} 