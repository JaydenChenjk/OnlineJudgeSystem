import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from ..models import data_store, Problem
from ..auth import require_admin, require_auth

router = APIRouter(prefix="/api", tags=["import_export"])

PROBLEMS_DIR = "problems"


@router.post("/reset/", summary="重置系统")
async def reset_system(request: Request):   # 重置系统（仅管理员）
    require_admin(request)  # 检查管理员权限
    
    # 清空所有数据文件
    data_store.reset_system()
    
    # 清空问题目录
    if os.path.exists(PROBLEMS_DIR):
        shutil.rmtree(PROBLEMS_DIR)
    os.makedirs(PROBLEMS_DIR, exist_ok=True)
    
    return {"code": 200, "msg": "system reset successfully", "data": None}


@router.get("/export/", summary="导出数据")
async def export_data(request: Request):   # 导出系统数据（仅管理员）
    require_admin(request)  # 检查管理员权限
    
    try:
        # 导出用户数据
        users_data = []
        for user in data_store.users.values():
            users_data.append({
                "user_id": user["user_id"],
                "username": user["username"],
                "password": user["password_hash"],  # 导出密码哈希
                "role": user["role"],
                "join_time": user["join_time"],
                "submit_count": user["submit_count"],
                "resolve_count": user["resolve_count"]
            })
        
        # 导出问题数据
        problems_data = []
        if os.path.exists(PROBLEMS_DIR):
            for filename in os.listdir(PROBLEMS_DIR):
                if filename.endswith('.json'):
                    problem_id = filename[:-5]
                    try:
                        with open(os.path.join(PROBLEMS_DIR, filename), 'r', encoding='utf-8') as f:
                            problem_data = json.load(f)
                            if "test_cases" in problem_data:  # 兼容旧格式
                                problem_data["testcases"] = problem_data.pop("test_cases")
                            problems_data.append(problem_data)
                    except Exception:
                        continue  # 跳过有问题的文件
        
        # 导出提交数据
        submissions_data = []
        for submission in data_store.submissions.values():
            submission_export = {
                "submission_id": submission["submission_id"],
                "user_id": submission["user_id"],
                "problem_id": submission["problem_id"],
                "language": submission["language"],
                "code": submission["code"],
                "score": submission["score"],
                "counts": submission["counts"]
            }
            
            # 添加评测详情
            if submission["submission_id"] in data_store.submission_logs:
                log = data_store.submission_logs[submission["submission_id"]]
                details = []
                for i, test_case in enumerate(log.get("test_cases", [])):
                    details.append({
                        "id": i + 1,
                        "result": test_case.get("status", "UNKNOWN"),
                        "time": test_case.get("time_used", 0),
                        "memory": test_case.get("memory_used", 0)
                    })
                submission_export["details"] = details
            else:
                submission_export["details"] = []
            
            submissions_data.append(submission_export)
        
        export_data = {
            "users": users_data,
            "problems": problems_data,
            "submissions": submissions_data
        }
        
        return {"code": 200, "msg": "success", "data": export_data}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"导出失败: {str(e)}"}
        )


@router.post("/import/", summary="导入数据")
async def import_data(request: Request, file: UploadFile = File(...)):  # 导入系统数据（仅管理员）
    require_admin(request)  # 检查管理员权限
    # 检查文件类型
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": "Only JSON files supported"}
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": "Empty file"}
        )
    try:
        data = json.loads(content.decode('utf-8'))
        # 验证数据格式
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail={"code": 400, "msg": "Invalid data format"}
            )
        # 导入用户数据
        if "users" in data and isinstance(data["users"], list):
            for user_data in data["users"]:
                if not isinstance(user_data, dict):
                    raise HTTPException(
                        status_code=400,
                        detail={"code": 400, "msg": "Invalid user data format"}
                    )
                required_fields = ["username", "password"]
                for field in required_fields:
                    if field not in user_data:
                        raise HTTPException(
                            status_code=400,
                            detail={"code": 400, "msg": f"Missing required field: {field}"}
                        )
                existing_user = data_store.get_user_by_username(user_data["username"])
                if not existing_user:
                    user_id = str(uuid.uuid4())
                    now = datetime.now().isoformat()
                    data_store.users[user_id] = {
                        "user_id": user_id,
                        "username": user_data["username"],
                        "password_hash": user_data["password"],
                        "role": user_data.get("role", "user"),
                        "join_time": user_data.get("join_time", now),
                        "submit_count": user_data.get("submit_count", 0),
                        "resolve_count": user_data.get("resolve_count", 0)
                    }
                else:
                    user_id = existing_user["user_id"]
                    data_store.users[user_id].update({
                        "role": user_data.get("role", "user"),
                        "submit_count": user_data.get("submit_count", 0),
                        "resolve_count": user_data.get("resolve_count", 0)
                    })
        # 导入问题数据
        if "problems" in data and isinstance(data["problems"], list):
            for problem_data in data["problems"]:
                if not (isinstance(problem_data, dict) and "id" in problem_data):
                    raise HTTPException(
                        status_code=400,
                        detail={"code": 400, "msg": "Invalid problem data format or missing id"}
                    )
                # 校验必需字段
                required_fields = [
                    "id", "title", "description", "input_description", "output_description",
                    "samples", "constraints", "testcases", "time_limit", "memory_limit"
                ]
                for field in required_fields:
                    if field not in problem_data:
                        raise HTTPException(
                            status_code=400,
                            detail={"code": 400, "msg": f"Missing required field: {field}"}
                        )
                os.makedirs(PROBLEMS_DIR, exist_ok=True)
                if "test_cases" in problem_data and "testcases" not in problem_data:
                    problem_data["testcases"] = problem_data.pop("test_cases")
                file_path = os.path.join(PROBLEMS_DIR, f"{problem_data['id']}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(problem_data, f, ensure_ascii=False, indent=2)
        # 导入提交数据
        if "submissions" in data and isinstance(data["submissions"], list):
            for submission_data in data["submissions"]:
                if isinstance(submission_data, dict) and "submission_id" in submission_data:
                    submission_id = submission_data["submission_id"]
                    data_store.submissions[submission_id] = {
                        "submission_id": submission_id,
                        "user_id": submission_data["user_id"],
                        "problem_id": submission_data["problem_id"],
                        "language": submission_data["language"],
                        "code": submission_data["code"],
                        "status": "completed",
                        "score": submission_data.get("score", 0),
                        "counts": submission_data.get("counts", 0),
                        "submit_time": submission_data.get("submit_time", "2024-01-01T00:00:00")
                    }
                    if "details" in submission_data and isinstance(submission_data["details"], list):
                        test_cases = []
                        for detail in submission_data["details"]:
                            test_cases.append({
                                "test_case_id": detail.get("id", 1),
                                "status": detail.get("result", "UNKNOWN"),
                                "time_used": detail.get("time", 0),
                                "memory_used": detail.get("memory", 0),
                                "input_data": "",
                                "expected_output": "",
                                "actual_output": ""
                            })
                        data_store.submission_logs[submission_id] = {
                            "submission_id": submission_id,
                            "user_id": submission_data["user_id"],
                            "problem_id": submission_data["problem_id"],
                            "language": submission_data["language"],
                            "code": submission_data["code"],
                            "score": submission_data.get("score", 0),
                            "counts": submission_data.get("counts", 0),
                            "test_cases": test_cases,
                            "submit_time": submission_data.get("submit_time", "2024-01-01T00:00:00")
                        }
        data_store.save_data()
        return {"code": 200, "msg": "import success", "data": None}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": "Invalid JSON format"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"导入失败: {str(e)}"}
        ) 