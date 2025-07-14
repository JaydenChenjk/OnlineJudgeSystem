from fastapi import APIRouter, Request, HTTPException, status, Query
from typing import Optional
from ..models import LogVisibilityConfig, data_store
from ..auth import require_auth, require_admin, get_current_user

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/submissions/{submission_id}/log", summary="获取提交日志")
async def get_submission_log(submission_id: str, request: Request):
    """获取提交日志（需要登录）"""
    current_user = require_auth(request)  # 需要登录
    
    try:
        # 获取提交信息
        submission = data_store.get_submission(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": "提交不存在"}
            )
        
        # 获取评测日志
        log_data = data_store.get_submission_log(submission_id)
        if not log_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": "评测日志不存在"}
            )
        
        # 检查权限
        can_view = False
        
        # 管理员可以查看所有日志
        if current_user["role"] == "admin":
            can_view = True
        # 用户只能查看自己的日志
        elif submission["user_id"] == current_user["user_id"]:
            can_view = True
        # 如果题目允许公开日志，所有登录用户都可以查看
        else:
            visibility = data_store.get_problem_visibility(submission["problem_id"])
            if visibility.get("public_cases", False):
                can_view = True
        
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 403, "msg": "权限不足"}
            )
        
        # 记录访问日志
        data_store.log_access(
            current_user["user_id"],
            current_user["username"],
            "view_submission_log",
            submission_id,
            "submission"
        )
        
        # 返回日志数据
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "score": log_data["score"],
                "counts": log_data["counts"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取提交日志失败: {str(e)}"}
        )


@router.put("/problems/{problem_id}/log_visibility", summary="配置日志可见性")
async def configure_log_visibility(problem_id: str, visibility_data: LogVisibilityConfig, request: Request):
    """配置日志可见性（仅管理员）"""
    require_admin(request)  # 检查管理员权限
    
    try:
        # 检查题目是否存在
        from .problems import load_problem
        try:
            load_problem(problem_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": "题目不存在"}
            )
        
        # 设置可见性
        data_store.set_problem_visibility(problem_id, visibility_data.public_cases)
        
        # 记录访问日志
        data_store.log_access(
            request.state.user["user_id"],
            request.state.user["username"],
            "configure_log_visibility",
            problem_id,
            "problem"
        )
        
        return {
            "code": 200,
            "msg": "log visibility updated",
            "data": {
                "problem_id": problem_id,
                "public_cases": visibility_data.public_cases
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"配置日志可见性失败: {str(e)}"}
        )


@router.get("/logs/access/", summary="获取访问审计日志")
async def get_access_logs(
    request: Request,
    user_id: Optional[str] = Query(None),
    problem_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1)
):
    """获取访问审计日志（仅管理员）"""
    require_admin(request)  # 检查管理员权限
    
    try:
        result = data_store.get_access_logs(user_id, problem_id, page, page_size)
        
        # 转换日志格式
        logs = []
        for log in result["logs"]:
            logs.append({
                "log_id": log["log_id"],
                "user_id": log["user_id"],
                "username": log["username"],
                "action": log["action"],
                "resource_id": log["resource_id"],
                "resource_type": log["resource_type"],
                "access_time": log["access_time"],
                "ip_address": log["ip_address"]
            })
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "total": result["total"],
                "logs": logs
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取访问日志失败: {str(e)}"}
        ) 