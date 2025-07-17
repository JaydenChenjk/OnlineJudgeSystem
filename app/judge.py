import asyncio
import subprocess
import tempfile
import os
import signal
import psutil
import time
from typing import Dict, List, Tuple, Optional
from .models import data_store
from .docker_judge import docker_judge


class JudgeResult:
    def __init__(self, status: str, score: int = 0, counts: int = 0):
        self.status = status  # pending, success, error
        self.score = score
        self.counts = counts


class TestCaseResult:
    def __init__(self, status: str, time_used: float = 0, memory_used: int = 0, input_data: str = "", expected_output: str = "", actual_output: str = ""):
        self.status = status  # AC, WA, TLE, MLE, RE, CE, UNK
        self.time_used = time_used
        self.memory_used = memory_used
        self.input_data = input_data
        self.expected_output = expected_output
        self.actual_output = actual_output


class Judge:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()  # 创建临时目录
    
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
            
            # 获取评测模式
            judge_mode = getattr(problem, 'judge_mode', 'standard')
            problem_id = submission["problem_id"]
            
            # 获取语言配置
            language = data_store.get_language(submission["language"])
            if not language:
                data_store.update_submission(submission_id, status="error")
                return JudgeResult("error")
            
            # 评测所有测试点
            test_cases = problem.testcases
            total_score = 0
            total_counts = len(test_cases) * 10  # 每个测试点10分
            
            test_case_results = []
            for i, test_case in enumerate(test_cases):
                result = await self._judge_test_case(
                    submission["code"],
                    submission["language"],
                    language,
                    test_case.input,
                    test_case.output,
                    problem.time_limit or language.get("time_limit", 3.0),
                    problem.memory_limit or language.get("memory_limit", 128),
                    i,
                    judge_mode,
                    problem_id
                )
                
                test_case_results.append({
                    "test_case_id": i,
                    "status": result.status,
                    "time_used": result.time_used,
                    "memory_used": result.memory_used,
                    "input_data": result.input_data,
                    "expected_output": result.expected_output,
                    "actual_output": result.actual_output
                })
                
                if result.status == "AC":
                    total_score += 10
            
            # 保存评测日志
            log_data = {
                "submission_id": submission_id,
                "user_id": submission["user_id"],
                "problem_id": submission["problem_id"],
                "language": submission["language"],
                "code": submission["code"],
                "score": total_score,
                "counts": total_counts,
                "test_cases": test_case_results,
                "submit_time": submission["submit_time"]
            }
            data_store.save_submission_log(submission_id, log_data)
            
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
        memory_limit: int,
        test_case_id: int,
        judge_mode: str = "standard",
        problem_id: str = ""
    ):
        """评测单个测试点（使用Docker安全评测）"""
        try:
            # 使用Docker评测器
            return await docker_judge.judge_test_case(
                code=code,
                language=language_name,
                input_data=input_data,
                expected_output=expected_output,
                time_limit=time_limit,
                memory_limit=memory_limit,
                judge_mode=judge_mode,
                problem_id=problem_id
            )
        except Exception as e:
            print(f"Test case error: {e}")
            return TestCaseResult(
                status="UNK",
                input_data=input_data,
                expected_output=expected_output,
                actual_output=""
            )
    
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
                return TestCaseResult(status="TLE", actual_output="")
            
            if process.returncode != 0:
                return TestCaseResult(status="CE", actual_output="")
            
            return TestCaseResult(status="AC", actual_output="")
            
        except Exception as e:
            print(f"Compile error: {e}")
            return TestCaseResult(status="CE", actual_output="")
    
    async def _run_code(
        self,
        run_cmd: str,
        code_file: str,
        input_data: str,
        expected_output: str,
        time_limit: float,
        memory_limit: int,
        judge_mode: str = "standard",
        problem_id: str = ""
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
                return TestCaseResult(
                    status="TLE",
                    time_used=time_limit,
                    input_data=input_data,
                    expected_output=expected_output,
                    actual_output=""
                )
            
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
                return TestCaseResult(
                    status="MLE",
                    time_used=time_used,
                    memory_used=memory_used,
                    input_data=input_data,
                    expected_output=expected_output,
                    actual_output=""
                )
            
            if process.returncode != 0:
                return TestCaseResult(
                    status="RE",
                    time_used=time_used,
                    memory_used=memory_used,
                    input_data=input_data,
                    expected_output=expected_output,
                    actual_output=""
                )
            
            # 比较输出
            actual_output = stdout.decode().rstrip()
            expected_output = expected_output.rstrip()
            
            # 根据评测模式进行判断
            if judge_mode == "spj" and problem_id:
                # 使用SPJ脚本进行评测
                try:
                    from .routers.spj import run_spj_script
                    spj_result = await run_spj_script(problem_id, input_data, expected_output, actual_output)
                    
                    if spj_result.get("status") == "AC":
                        return TestCaseResult(
                            status="AC",
                            time_used=time_used,
                            memory_used=memory_used,
                            input_data=input_data,
                            expected_output=expected_output,
                            actual_output=actual_output
                        )
                    else:
                        return TestCaseResult(
                            status="WA",
                            time_used=time_used,
                            memory_used=memory_used,
                            input_data=input_data,
                            expected_output=expected_output,
                            actual_output=actual_output
                        )
                except Exception as e:
                    print(f"SPJ评测失败: {e}")
                    # SPJ失败时回退到标准评测
                    pass
            
            # 标准评测或严格评测
            if judge_mode == "strict":
                # 严格模式：完全匹配
                if actual_output == expected_output:
                    return TestCaseResult(
                        status="AC",
                        time_used=time_used,
                        memory_used=memory_used,
                        input_data=input_data,
                        expected_output=expected_output,
                        actual_output=actual_output
                    )
                else:
                    return TestCaseResult(
                        status="WA",
                        time_used=time_used,
                        memory_used=memory_used,
                        input_data=input_data,
                        expected_output=expected_output,
                        actual_output=actual_output
                    )
            else:
                # 标准模式：忽略多余空格和换行
                if self._normalize_output(actual_output) == self._normalize_output(expected_output):
                    return TestCaseResult(
                        status="AC",
                        time_used=time_used,
                        memory_used=memory_used,
                        input_data=input_data,
                        expected_output=expected_output,
                        actual_output=actual_output
                    )
                else:
                    return TestCaseResult(
                        status="WA",
                        time_used=time_used,
                        memory_used=memory_used,
                        input_data=input_data,
                        expected_output=expected_output,
                        actual_output=actual_output
                    )
            
        except Exception as e:
            print(f"Run error: {e}")
            return TestCaseResult(
                status="UNK",
                input_data=input_data,
                expected_output=expected_output,
                actual_output=""
            )
    
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