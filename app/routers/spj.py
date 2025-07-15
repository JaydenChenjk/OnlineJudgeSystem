import os
import json
import tempfile
import subprocess
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from ..models import data_store
from ..auth import require_auth, require_admin

router = APIRouter(prefix="/api/spj", tags=["spj"])

SPJ_DIR = "spj_scripts"  # SPJ脚本存储目录
os.makedirs(SPJ_DIR, exist_ok=True)

# 允许的脚本文件扩展名
ALLOWED_EXTENSIONS = {".py", ".js", ".sh"}

'''
DANGEROUS_FUNCTIONS = {
    "eval", "exec", "compile", "open", "file", "__import__", "globals", "locals",
    "input", "raw_input", "system", "popen", "subprocess", "os.system", "subprocess.call",
    "subprocess.Popen", "subprocess.run", "reload"
}
'''

def validate_spj_script(content: str) -> bool:
    """验证SPJ脚本内容的安全性"""
    content_lower = content.lower()
    
    # 只检查最危险的函数
    extremely_dangerous = ["eval(", "exec(", "os.system(", "subprocess.call(", "subprocess.run("]
    for func in extremely_dangerous:
        if func in content_lower:
            return False
    
    return True


def get_spj_file_path(problem_id: str) -> str:
    """获取SPJ脚本文件路径"""
    return os.path.join(SPJ_DIR, f"{problem_id}.py")


def save_spj_script(problem_id: str, content: str) -> None:
    """保存SPJ脚本"""
    file_path = get_spj_file_path(problem_id)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def load_spj_script(problem_id: str) -> Optional[str]:
    """加载SPJ脚本"""
    file_path = get_spj_file_path(problem_id)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def delete_spj_script(problem_id: str) -> bool:
    """删除SPJ脚本"""
    file_path = get_spj_file_path(problem_id)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False


async def run_spj_script(problem_id: str, input_data: str, expected_output: str, actual_output: str) -> dict:
    """运行SPJ脚本进行评测"""
    script_content = load_spj_script(problem_id)
    if not script_content:
        raise Exception("SPJ脚本不存在")
    
    # 创建临时脚本文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_file = f.name
    
    try:
        # 运行SPJ脚本
        process = await asyncio.create_subprocess_exec(
            "python", script_file,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 准备输入数据（JSON格式）
        input_json = json.dumps({
            "input": input_data,
            "expected_output": expected_output,
            "actual_output": actual_output
        })
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=input_json.encode()),
            timeout=10.0  # 10秒超时
        )
        
        if process.returncode != 0:
            return {
                "status": "SPJ_ERROR",
                "message": stderr.decode() if stderr else "SPJ脚本执行失败"
            }
        
        # 解析SPJ输出
        try:
            result = json.loads(stdout.decode())
            return result
        except json.JSONDecodeError:
            return {
                "status": "SPJ_ERROR",
                "message": "SPJ脚本输出格式错误"
            }
    
    except asyncio.TimeoutError:
        return {
            "status": "SPJ_ERROR",
            "message": "SPJ脚本执行超时"
        }
    except Exception as e:
        return {
            "status": "SPJ_ERROR",
            "message": f"SPJ脚本执行异常: {str(e)}"
        }
    finally:
        # 清理临时文件
        try:
            os.unlink(script_file)
        except:
            pass


@router.post("/upload/{problem_id}", summary="上传SPJ脚本")
async def upload_spj_script(
    problem_id: str,
    file: UploadFile = File(...),
    request: Request = None
):
    """上传SPJ脚本（仅管理员）"""
    require_admin(request)
    
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": f"不支持的文件类型: {file_ext}，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"}
        )
    
    # 读取文件内容
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": "文件编码错误，请使用UTF-8编码"}
        )
    
    # 验证脚本内容安全性
    if not validate_spj_script(content_str):
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": "脚本内容包含危险操作，请检查后重新上传"}
        )
    
    # 保存脚本
    try:
        save_spj_script(problem_id, content_str)
        return {"code": 200, "msg": "SPJ脚本上传成功", "data": None}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"保存SPJ脚本失败: {str(e)}"}
        )


@router.post("/upload_text/{problem_id}", summary="上传SPJ脚本文本")
async def upload_spj_text(
    problem_id: str,
    script_content: str = Form(...),
    request: Request = None
):
    """上传SPJ脚本文本内容（仅管理员）"""
    require_admin(request)
    
    # 验证脚本内容安全性
    if not validate_spj_script(script_content):
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "msg": "脚本内容包含危险操作，请检查后重新上传"}
        )
    
    # 保存脚本
    try:
        save_spj_script(problem_id, script_content)
        return {"code": 200, "msg": "SPJ脚本上传成功", "data": None}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"保存SPJ脚本失败: {str(e)}"}
        )


@router.get("/{problem_id}", summary="获取SPJ脚本")
async def get_spj_script(problem_id: str, request: Request = None):
    """获取SPJ脚本（仅管理员）"""
    require_admin(request)
    
    script_content = load_spj_script(problem_id)
    if not script_content:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "msg": "SPJ脚本不存在"}
        )
    
    return {"code": 200, "msg": "success", "data": {"script": script_content}}


@router.delete("/{problem_id}", summary="删除SPJ脚本")
async def delete_spj_script_endpoint(problem_id: str, request: Request = None):
    """删除SPJ脚本（仅管理员）"""
    require_admin(request)
    
    if delete_spj_script(problem_id):
        return {"code": 200, "msg": "SPJ脚本删除成功", "data": None}
    else:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "msg": "SPJ脚本不存在"}
        )


@router.post("/test/{problem_id}", summary="测试SPJ脚本")
async def test_spj_script(
    problem_id: str,
    input_data: str = Form(...),
    expected_output: str = Form(...),
    actual_output: str = Form(...),
    request: Request = None
):
    """测试SPJ脚本（仅管理员）"""
    require_admin(request)
    
    try:
        result = await run_spj_script(problem_id, input_data, expected_output, actual_output)
        return {"code": 200, "msg": "SPJ脚本测试完成", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"SPJ脚本测试失败: {str(e)}"}
        ) 