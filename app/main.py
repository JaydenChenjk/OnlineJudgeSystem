import json
import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Online Judge System", version="1.0.0")

class Sample(BaseModel):
    input: str
    output: str

class TestCase(BaseModel):
    input: str
    output: str

class Problem(BaseModel):
    id: str = Field(..., description="题目唯一标识")
    title: str = Field(..., description="题目标题")
    description: str = Field(..., description="题目描述")
    input_description: str = Field(..., description="输入格式说明")
    output_description: str = Field(..., description="输出格式说明")
    samples: List[Sample] = Field(..., description="样例输入输出")
    constraints: str = Field(..., description="数据范围和限制条件")
    testcases: List[TestCase] = Field(..., description="测试点")  # 改回testcases
    hint: Optional[str] = Field("", description="额外提示")  # 默认空字符串
    source: Optional[str] = Field("", description="题目来源或出处")
    tags: Optional[List[str]] = Field([], description="题目标签")  # 默认空列表
    time_limit: Optional[float] = Field(3.0, description="时间限制")  # 默认3.0秒
    memory_limit: Optional[int] = Field(128, description="内存限制")  # 默认128MB
    author: Optional[str] = Field("", description="题目作者")
    difficulty: Optional[str] = Field("", description="难度等级")

class ProblemSummary(BaseModel):
    id: str
    title: str

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
            detail=f"题目 {problem_id} 不存在"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"题目 {problem_id} 配置文件格式错误"
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
            detail=f"保存题目失败: {str(e)}"
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

@app.get("/")
async def welcome():
    return "Welcome!"

@app.get("/api/problems/", summary="获取题目列表")
async def get_problems():
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
            detail=f"获取题目列表失败: {str(e)}"
        )

@app.get("/api/problems/{problem_id}", summary="获取题目详情")
async def get_problem(problem_id: str):
    try:
        problem = load_problem(problem_id)  # 返回完整题目信息
        return {"code": 200, "msg": "success", "data": problem}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取题目详情失败: {str(e)}"
        )

@app.post("/api/problems/", summary="添加题目")
async def create_problem(problem: Problem):
    try:
        file_path = get_problem_file_path(problem.id)
        if os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"题目 {problem.id} 已存在"
            )  # 检查题目是否已存在
        
        save_problem(problem)  # 保存新题目
        return {"code": 200, "msg": "add success", "data": {"id": problem.id}}  # 标准响应格式
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建题目失败: {str(e)}"
        )

@app.delete("/api/problems/{problem_id}", summary="删除题目")
async def delete_problem(problem_id: str):
    try:
        file_path = get_problem_file_path(problem_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"题目 {problem_id} 不存在"
            )  # 检查题目是否存在
        
        os.remove(file_path)  # 删除题目文件
        
        return {"code": 200, "msg": "delete success", "data": {"id": problem_id}}  # 标准响应格式
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除题目失败: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # 启动服务器 