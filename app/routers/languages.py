from fastapi import APIRouter, Request, HTTPException, status
from ..models import Language, data_store
from ..auth import require_admin, get_current_user

router = APIRouter(prefix="/api/languages", tags=["languages"])


@router.post("/", summary="注册新语言")
async def register_language(language_data: Language, request: Request):
    """注册新语言（仅管理员）"""
    require_admin(request)  # 检查管理员权限
    
    try:
        data_store.register_language(language_data.model_dump())
        return {"code": 200, "msg": "language registered", "data": {"name": language_data.name}}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "msg": str(e)}
        )


@router.get("/", summary="获取支持的语言列表")
async def get_supported_languages(request: Request):
    """获取支持的语言列表（需要登录）"""
    get_current_user(request)  # 需要登录
    
    try:
        languages = data_store.get_languages()
        return {"code": 200, "msg": "success", "data": languages}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取语言列表失败: {str(e)}"}
        ) 