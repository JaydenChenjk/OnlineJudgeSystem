import asyncio
import subprocess
import tempfile
import os
import signal
import psutil
import time
from typing import Dict, List, Tuple, Optional
from .models import data_store


class JudgeResult:
    def __init__(self, status: str, score: int = 0, counts: int = 0):
        self.status = status  # pending, success, error
        self.score = score
        self.counts = counts


class TestCaseResult:
    def __init__(self, status: str, time_used: float = 0, memory_used: int = 0):
        self.status = status  # AC, WA, TLE, MLE, RE, CE, UNK
        self.time_used = time_used
        self.memory_used = memory_used


class Judge:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    async def judge_submission(self, submission_id: str) -> JudgeResult:
        """评测提交"""
        try:
            submission = data_store.get_submission(submission_id)
            if not submission:
                return JudgeResult("error")
            
            # 获取题目信息
            problem = self._load_problem(submission["problem_id"])
            if not problem:
                data_store.update_submission(submission_id, status="error")
                return JudgeResult("error")
            
            # 获取语言配置
            language = data_store.get_language(submission["language"])
            if not language:
                data_store.update_submission(submission_id, status="error")
                return JudgeResult("error")
            
            # 评测所有测试点
            test_cases = problem.testcases
            total_score = 0
            total_counts = len(test_cases) * 10  # 每个测试点10分
            
            for i, test_case in enumerate(test_cases):
                result = await self._judge_test_case(
                    submission["code"],
                    submission["language"],
                    language,
                    test_case.input,
                    test_case.output,
                    problem.time_limit or language.get("time_limit", 3.0),
                    problem.memory_limit or language.get("memory_limit", 128)
                )
                
                if result.status == "AC":
                    total_score += 10
            
            # 更新提交结果
            data_store.update_submission(
                submission_id,
                status="success",
                score=total_score,
                counts=total_counts
            )
            
            return JudgeResult("success", total_score, total_counts)
            
        except Exception as e:
            print(f"Judge error: {e}")
            data_store.update_submission(submission_id, status="error")
            return JudgeResult("error")
    
    def _load_problem(self, problem_id: str):
        """加载题目信息"""
        import json
        from .routers.problems import load_problem
        
        try:
            return load_problem(problem_id)
        except:
            return None
    
    async def _judge_test_case(
        self,
        code: str,
        language_name: str,
        language_config: dict,
        input_data: str,
        expected_output: str,
        time_limit: float,
        memory_limit: int
    ) -> TestCaseResult:
        """评测单个测试点"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=language_config["file_ext"],
                delete=False,
                dir=self.temp_dir
            ) as f:
                f.write(code)
                code_file = f.name
            
            # 编译（如果需要）
            if language_config.get("compile_cmd"):
                compile_result = await self._compile_code(
                    language_config["compile_cmd"],
                    code_file,
                    time_limit
                )
                if compile_result.status != "AC":
                    os.unlink(code_file)
                    return compile_result
            
            # 运行代码
            run_result = await self._run_code(
                language_config["run_cmd"],
                code_file,
                input_data,
                expected_output,
                time_limit,
                memory_limit
            )
            
            # 清理临时文件
            try:
                os.unlink(code_file)
                # 清理编译产物
                if language_name == "cpp":
                    exe_file = code_file.replace(".cpp", "")
                    if os.path.exists(exe_file):
                        os.unlink(exe_file)
            except:
                pass
            
            return run_result
            
        except Exception as e:
            print(f"Test case error: {e}")
            return TestCaseResult("UNK")
    
    async def _compile_code(self, compile_cmd: str, code_file: str, time_limit: float) -> TestCaseResult:
        """编译代码"""
        try:
            # 替换命令中的文件名
            cmd = compile_cmd.replace("main.cpp", os.path.basename(code_file))
            
            process = await asyncio.create_subprocess_exec(
                *cmd.split(),
                cwd=os.path.dirname(code_file),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=time_limit)
            except asyncio.TimeoutError:
                process.kill()
                return TestCaseResult("TLE")
            
            if process.returncode != 0:
                return TestCaseResult("CE")
            
            return TestCaseResult("AC")
            
        except Exception as e:
            print(f"Compile error: {e}")
            return TestCaseResult("CE")
    
    async def _run_code(
        self,
        run_cmd: str,
        code_file: str,
        input_data: str,
        expected_output: str,
        time_limit: float,
        memory_limit: int
    ) -> TestCaseResult:
        """运行代码"""
        try:
            # 替换命令中的文件名
            cmd = run_cmd.replace("main.py", os.path.basename(code_file))
            if "main" in cmd and not cmd.endswith(".py"):
                cmd = cmd.replace("main", os.path.splitext(os.path.basename(code_file))[0])
            
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                *cmd.split(),
                cwd=os.path.dirname(code_file),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data.encode()),
                    timeout=time_limit
                )
            except asyncio.TimeoutError:
                process.kill()
                return TestCaseResult("TLE")
            
            end_time = time.time()
            time_used = end_time - start_time
            
            # 检查内存使用（简化实现）
            memory_used = 0
            try:
                if process.pid:
                    p = psutil.Process(process.pid)
                    memory_used = p.memory_info().rss // 1024 // 1024  # MB
            except:
                pass
            
            if memory_used > memory_limit:
                return TestCaseResult("MLE", time_used, memory_used)
            
            if process.returncode != 0:
                return TestCaseResult("RE", time_used, memory_used)
            
            # 比较输出
            actual_output = stdout.decode().rstrip()
            expected_output = expected_output.rstrip()
            
            if self._normalize_output(actual_output) == self._normalize_output(expected_output):
                return TestCaseResult("AC", time_used, memory_used)
            else:
                return TestCaseResult("WA", time_used, memory_used)
            
        except Exception as e:
            print(f"Run error: {e}")
            return TestCaseResult("UNK")
    
    def _normalize_output(self, output: str) -> str:
        """标准化输出，忽略多余的空格和换行"""
        lines = output.split('\n')
        normalized_lines = []
        for line in lines:
            normalized_lines.append(line.rstrip())
        return '\n'.join(normalized_lines).rstrip()
    
    def cleanup(self):
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass


# 全局评测器实例
judge = Judge() 