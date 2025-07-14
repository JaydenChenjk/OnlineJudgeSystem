import json
import os
from typing import List
from fastapi import APIRouter, HTTPException, status, Request
from ..models import Problem, ProblemSummary, data_store
from ..auth import require_auth, require_admin, get_current_user

router = APIRouter(prefix="/api/problems", tags=["problems"])

PROBLEMS_DIR = "problems"  # 题目配置文件目录
os.makedirs(PROBLEMS_DIR, exist_ok=True)  # 确保目录存在


def get_problem_file_path(problem_id: str) -> str:
    return os.path.join(PROBLEMS_DIR, f"{problem_id}.json")  # 获取题目文件路径


def load_problem(problem_id: str) -> Problem:
    file_path = get_problem_file_path(problem_id)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "test_cases" in data:  # 兼容旧格式
                data["testcases"] = data.pop("test_cases")
            return Problem(**data)  # 从JSON加载题目配置
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "msg": f"题目 {problem_id} 不存在"}
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"题目 {problem_id} 配置文件格式错误"}
        )


def save_problem(problem: Problem) -> None:
    file_path = get_problem_file_path(problem.id)
    try:
        problem_dict = problem.model_dump()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(problem_dict, f, ensure_ascii=False, indent=2)  # 保存题目到JSON文件
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"保存题目失败: {str(e)}"}
        )


def get_all_problem_ids() -> List[str]:
    if not os.path.exists(PROBLEMS_DIR):
        return []
    
    problem_ids = []
    for filename in os.listdir(PROBLEMS_DIR):
        if filename.endswith('.json'):
            problem_id = filename[:-5]  # 移除.json后缀
            problem_ids.append(problem_id)
    return sorted(problem_ids)  # 返回排序后的题目ID列表


@router.get("/", summary="获取题目列表")
async def get_problems(request: Request):
    """获取题目列表（需要登录）"""
    require_auth(request)  # 需要登录
    
    try:
        problem_ids = get_all_problem_ids()
        problems = []
        
        for problem_id in problem_ids:
            try:
                problem = load_problem(problem_id)
                problems.append(ProblemSummary(
                    id=problem.id,
                    title=problem.title
                ))  # 构建题目摘要信息
            except HTTPException:
                continue  # 跳过有问题的配置文件
        
        return {"code": 200, "msg": "success", "data": problems}  # 标准响应格式
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取题目列表失败: {str(e)}"}
        )


@router.get("/{problem_id}", summary="获取题目详情")
async def get_problem(problem_id: str, request: Request):
    """获取题目详情（需要登录）"""
    require_auth(request)  # 需要登录
    
    try:
        problem = load_problem(problem_id)  # 返回完整题目信息
        return {"code": 200, "msg": "success", "data": problem}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"获取题目详情失败: {str(e)}"}
        )


@router.post("/", summary="添加题目")
async def create_problem(problem: Problem, request: Request):
    """添加题目（需要登录）"""
    require_auth(request)  # 需要登录
    
    try:
        file_path = get_problem_file_path(problem.id)
        if os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 409, "msg": f"题目 {problem.id} 已存在"}
            )  # 检查题目是否已存在
        
        save_problem(problem)  # 保存新题目
        return {"code": 200, "msg": "add success", "data": {"id": problem.id}}  # 标准响应格式
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"创建题目失败: {str(e)}"}
        )


@router.delete("/{problem_id}", summary="删除题目")
async def delete_problem(problem_id: str, request: Request):
    """删除题目（仅管理员）"""
    require_admin(request)  # 仅管理员可删除
    
    try:
        file_path = get_problem_file_path(problem_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": 404, "msg": f"题目 {problem_id} 不存在"}
            )  # 检查题目是否存在
        
        os.remove(file_path)  # 删除题目文件
        
        return {"code": 200, "msg": "delete success", "data": {"id": problem_id}}  # 标准响应格式
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "msg": f"删除题目失败: {str(e)}"}
        ) 