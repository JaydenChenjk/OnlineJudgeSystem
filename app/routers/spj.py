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

router = APIRouter(prefix="/api/problems", tags=["spj"])

SPJ_DIR = "spj_scripts"  # SPJ脚本存储目录
os.makedirs(SPJ_DIR, exist_ok=True)

# 允许的脚本文件扩展名
ALLOWED_EXTENSIONS = {".py", ".cpp"}

def validate_spj_script(content: str) -> bool:
    """验证SPJ脚本内容的安全性"""
    content_lower = content.lower()
    
    # 只检查最危险的函数
    extremely_dangerous = ["eval(", "exec(", "os.system(", "subprocess.call(", "subprocess.run("]
    for func in extremely_dangerous:
        if func in content_lower:
            return False
    
    return True


def get_spj_file_path(problem_id: str, file_ext: str = ".py") -> str:
    """获取SPJ脚本文件路径"""
    return os.path.join(SPJ_DIR, f"{problem_id}{file_ext}")


def save_spj_script(problem_id: str, content: str, file_ext: str = ".py") -> None:
    """保存SPJ脚本"""
    file_path = get_spj_file_path(problem_id, file_ext)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def load_spj_script(problem_id: str) -> Optional[str]:
    """加载SPJ脚本"""
    # 尝试加载.py文件
    py_path = get_spj_file_path(problem_id, ".py")
    if os.path.exists(py_path):
        with open(py_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # 尝试加载.cpp文件
    cpp_path = get_spj_file_path(problem_id, ".cpp")
    if os.path.exists(cpp_path):
        with open(cpp_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    return None


def delete_spj_script(problem_id: str) -> bool:
    """删除SPJ脚本"""
    deleted = False
    
    # 尝试删除.py文件
    py_path = get_spj_file_path(problem_id, ".py")
    if os.path.exists(py_path):
        os.remove(py_path)
        deleted = True
    
    # 尝试删除.cpp文件
    cpp_path = get_spj_file_path(problem_id, ".cpp")
    if os.path.exists(cpp_path):
        os.remove(cpp_path)
        deleted = True
    
    return deleted


async def run_spj_script(problem_id: str, input_data: str, expected_output: str, actual_output: str) -> dict:
    """运行SPJ脚本进行评测"""
    script_content = load_spj_script(problem_id)
    if not script_content:
        raise Exception("SPJ脚本不存在")
    
    # 确定脚本类型和文件扩展名
    py_path = get_spj_file_path(problem_id, ".py")
    cpp_path = get_spj_file_path(problem_id, ".cpp")
    
    if os.path.exists(py_path):
        # Python脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_file = f.name
        cmd = ["python", script_file]
    elif os.path.exists(cpp_path):
        # C++脚本，需要编译
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
            f.write(script_content)
            cpp_file = f.name
        
        # 编译C++代码
        exe_file = cpp_file.replace('.cpp', '.exe')
        compile_process = await asyncio.create_subprocess_exec(
            "g++", "-o", exe_file, cpp_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        compile_stdout, compile_stderr = await compile_process.communicate()
        if compile_process.returncode != 0:
            return {
                "status": "SPJ_ERROR",
                "message": f"C++编译失败: {compile_stderr.decode()}"
            }
        
        script_file = exe_file
        cmd = [exe_file]
    else:
        raise Exception("SPJ脚本文件不存在")
    
    try:
        # 运行SPJ脚本
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 准备输入数据
        if os.path.exists(py_path):
            # Python脚本使用JSON格式
            input_json = json.dumps({
                "input": input_data,
                "expected_output": expected_output,
                "actual_output": actual_output
            })
            input_bytes = input_json.encode()
        else:
            # C++脚本使用简单文本格式
            input_text = f"{input_data}\n{expected_output}\n{actual_output}\n"
            input_bytes = input_text.encode()
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=input_bytes),
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
            # 如果是C++脚本，还需要清理编译文件
            if 'exe_file' in locals():
                try:
                    os.unlink(exe_file)
                except:
                    pass
                try:
                    os.unlink(cpp_file)
                except:
                    pass
        except:
            pass

# 上传SPJ脚本：POST /api/problems/{problem_id}/spj
@router.post("/{problem_id}/spj")
async def upload_spj_script(problem_id: str, file: UploadFile = File(...), request: Request = None):
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
        save_spj_script(problem_id, content_str, file_ext)
        return {"code": 200, "msg": "SPJ脚本上传成功", "data": None}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"保存SPJ脚本失败: {str(e)}"}
        )


# 删除SPJ脚本：DELETE /api/problems/{problem_id}/spj
@router.delete("/{problem_id}/spj")
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


# 保留其他辅助接口（用于测试和管理）
@router.post("/{problem_id}/spj/text", summary="上传SPJ脚本文本")
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
    
    # 保存脚本（默认使用Python扩展名）
    try:
        save_spj_script(problem_id, script_content, ".py")
        return {"code": 200, "msg": "SPJ脚本上传成功", "data": None}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "msg": f"保存SPJ脚本失败: {str(e)}"}
        )


@router.get("/{problem_id}/spj", summary="获取SPJ脚本")
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


@router.post("/{problem_id}/spj/test", summary="测试SPJ脚本")
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