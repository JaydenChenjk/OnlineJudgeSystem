import asyncio
import os
from fastapi import APIRouter, Request, HTTPException, status, Query
from typing import Optional
from ..models import SubmissionCreate, data_store
from ..auth import require_auth, require_admin, get_current_user
from ..judge import judge

def is_testing():
    """检测是否在测试环境中"""
    return "PYTEST_CURRENT_TEST" in os.environ

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("/", summary="提交代码")
async def submit_solution(submission_data: SubmissionCreate, request: Request):
    """提交代码（需要登录）"""
    current_user = require_auth(request)  # 需要登录
    
    try:
        # 检查题目是否存在
        from .problems import load_problem
        try:
            load_problem(submission_data.problem_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": "题目不存在"}
            )
        
        # 检查语言是否支持
        language = data_store.get_language(submission_data.language)
        if not language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 400, "msg": "不支持的语言"}
            )
        
        # 创建提交
        submission_id = data_store.create_submission(
            current_user["user_id"],
            submission_data.problem_id,
            submission_data.language,
            submission_data.code
        )
        
        # 根据环境决定评测方式
        if is_testing():
            # 测试环境中直接等待评测完成
            await judge.judge_submission(submission_id)
        else:
            # 生产环境中异步评测
            asyncio.create_task(judge.judge_submission(submission_id))
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "submission_id": submission_id,
                "status": "pending"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"提交失败: {str(e)}"}
        )


@router.get("/{submission_id}", summary="获取提交结果")
async def get_submission_result(submission_id: str, request: Request):
    """获取提交结果（需要登录）"""
    current_user = require_auth(request)  # 需要登录
    
    try:
        submission = data_store.get_submission(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": "提交不存在"}
            )
        
        # 检查权限：只能查看自己的提交或管理员可以查看所有
        if submission["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 403, "msg": "权限不足"}
            )
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "submission_id": submission["submission_id"],
                "status": submission["status"],
                "score": submission["score"],
                "counts": submission["counts"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取提交结果失败: {str(e)}"}
        )


@router.get("/", summary="获取提交列表")
async def get_submissions_list(
    request: Request,
    user_id: Optional[str] = Query(None),
    problem_id: Optional[str] = Query(None),
    judge_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1)
):
    """获取提交列表（需要登录）"""
    current_user = require_auth(request)  # 需要登录
    
    # 检查参数：必须提供user_id或problem_id
    if not user_id and not problem_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "msg": "必须提供user_id或problem_id"}
        )
    
    # 检查权限：只能查看自己的提交或管理员可以查看所有
    if user_id and user_id != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "msg": "权限不足"}
        )
    
    try:
        result = data_store.get_submissions(user_id, problem_id, judge_status, page, page_size)
        
        # 转换提交信息格式
        submissions = []
        for submission in result["submissions"]:
            submissions.append({
                "submission_id": submission["submission_id"],
                "user_id": submission["user_id"],
                "problem_id": submission["problem_id"],
                "language": submission["language"],
                "status": submission["status"],
                "score": submission["score"],
                "counts": submission["counts"],
                "submit_time": submission["submit_time"]
            })
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "total": result["total"],
                "submissions": submissions
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取提交列表失败: {str(e)}"}
        )


@router.put("/{submission_id}/rejudge", summary="重新评测")
async def rejudge_submission(submission_id: str, request: Request):
    """重新评测（仅管理员）"""
    require_admin(request)  # 检查管理员权限
    
    try:
        submission = data_store.get_submission(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": "提交不存在"}
            )
        
        # 重置状态
        data_store.update_submission(
            submission_id,
            status="pending",
            score=0,
            counts=0
        )
        
        # 异步重新评测
        asyncio.create_task(judge.judge_submission(submission_id))
        
        return {
            "code": 200,
            "msg": "rejudge started",
            "data": {
                "submission_id": submission_id,
                "status": "pending"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"重新评测失败: {str(e)}"}
        ) 