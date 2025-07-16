import asyncio
import json
import os
import tempfile
import subprocess
import time
import uuid
from typing import Optional, Dict, Any


class DockerJudge:
    """Docker安全评测器"""
    
    def __init__(self):
        self.base_images = {
            "python": "python:3.9-slim",
            "cpp": "gcc:11"
        }
        self.container_prefix = "oj_judge_"
        self.ensure_images()
    
    def ensure_images(self):
        """确保Docker镜像存在"""
        # 检查Docker是否可用
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print("Docker不可用，将使用模拟模式")
                self.docker_available = False
                return
        except FileNotFoundError:
            print("Docker未安装，将使用模拟模式")
            self.docker_available = False
            return
        
        self.docker_available = True
        for lang, image in self.base_images.items():
            try:
                # 检查镜像是否存在
                result = subprocess.run(
                    ["docker", "images", "-q", image],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if not result.stdout.strip():
                    print(f"拉取Docker镜像: {image}")
                    subprocess.run(
                        ["docker", "pull", image],
                        timeout=60
                    )
            except Exception as e:
                print(f"确保镜像失败 {image}: {e}")
    
    def validate_command(self, cmd: str) -> bool:
        """验证命令安全性"""
        # 命令白名单
        allowed_commands = {
            "python", "python3", "gcc", "g++", "make", "cc", "c++"
        }
        
        # 危险命令黑名单
        dangerous_commands = {
            "rm", "rmdir", "del", "format", "mkfs", "dd", "shred",
            "sudo", "su", "chmod", "chown", "mount", "umount",
            "iptables", "firewall", "service", "systemctl",
            "ssh", "scp", "wget", "curl", "nc", "telnet",
            "docker", "kubectl", "kubectl", "helm"
        }
        
        # 危险参数
        dangerous_flags = {
            "-rf", "--recursive", "--force", "--no-preserve-root",
            "--preserve-root=0", "-exec", "-ok", "-delete"
        }
        
        cmd_parts = cmd.lower().split()
        if not cmd_parts:
            return False
        
        # 检查主命令
        main_cmd = cmd_parts[0]
        if main_cmd in dangerous_commands:
            return False
        
        # 检查参数
        for part in cmd_parts[1:]:
            if part in dangerous_flags:
                return False
            if part.startswith("-") and any(flag in part for flag in dangerous_flags):
                return False
        
        return True
    
    def create_dockerfile(self, language: str, code_file: str, work_dir: str) -> str:
        """创建Dockerfile"""
        if language == "python":
            dockerfile_content = f"""
FROM {self.base_images[language]}
WORKDIR {work_dir}
COPY {os.path.basename(code_file)} .
CMD ["python", "{os.path.basename(code_file)}"]
"""
        elif language == "cpp":
            dockerfile_content = f"""
FROM {self.base_images[language]}
WORKDIR {work_dir}
COPY {os.path.basename(code_file)} .
RUN g++ -o main {os.path.basename(code_file)}
CMD ["./main"]
"""
        else:
            raise ValueError(f"不支持的语言: {language}")
        
        dockerfile_path = os.path.join(os.path.dirname(code_file), "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        return dockerfile_path
    
    async def run_in_docker(
        self,
        language: str,
        code_file: str,
        input_data: str,
        time_limit: float,
        memory_limit: int,
        container_name: str
    ) -> Dict[str, Any]:
        """在Docker容器中运行代码"""
        # 如果Docker不可用，使用模拟模式
        if not getattr(self, 'docker_available', True):
            return await self._run_simulation(language, code_file, input_data, time_limit, memory_limit)
        
        try:
            work_dir = "/workspace"
            dockerfile_path = self.create_dockerfile(language, code_file, work_dir)
            
            # 构建Docker镜像
            image_name = f"{container_name}_image"
            build_cmd = [
                "docker", "build", "-t", image_name,
                "-f", dockerfile_path,
                os.path.dirname(code_file)
            ]
            
            if not self.validate_command(" ".join(build_cmd)):
                return {"status": "CE", "error": "构建命令不安全"}
            
            build_process = await asyncio.create_subprocess_exec(
                *build_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    build_process.communicate(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                build_process.kill()
                return {"status": "CE", "error": "构建超时"}
            
            if build_process.returncode != 0:
                return {"status": "CE", "error": stderr.decode()}
            
            # 运行Docker容器
            run_cmd = [
                "docker", "run",
                "--name", container_name,
                "--rm",  # 自动删除容器
                "--network", "none",  # 禁用网络
                "--memory", f"{memory_limit}m",  # 内存限制
                "--cpus", str(time_limit),  # CPU时间限制
                "--pids-limit", "50",  # 进程数限制
                "--ulimit", "nofile=64:64",  # 文件描述符限制
                "--security-opt", "no-new-privileges",  # 禁止提权
                "--cap-drop", "ALL",  # 删除所有权限
                "--read-only",  # 只读文件系统
                "--tmpfs", f"{work_dir}:rw,noexec,nosuid,size=100m",  # 临时文件系统
                image_name
            ]
            
            if not self.validate_command(" ".join(run_cmd)):
                return {"status": "CE", "error": "运行命令不安全"}
            
            start_time = time.time()
            run_process = await asyncio.create_subprocess_exec(
                *run_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    run_process.communicate(input=input_data.encode()),
                    timeout=time_limit + 1.0  # 额外1秒缓冲
                )
            except asyncio.TimeoutError:
                run_process.kill()
                # 强制停止容器
                await asyncio.create_subprocess_exec("docker", "kill", container_name)
                return {"status": "TLE", "time_used": time_limit}
            
            end_time = time.time()
            time_used = end_time - start_time
            
            # 检查容器退出状态
            if run_process.returncode != 0:
                return {
                    "status": "RE",
                    "time_used": time_used,
                    "error": stderr.decode()
                }
            
            # 获取内存使用情况
            memory_used = 0
            try:
                stats_cmd = ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_name]
                stats_process = await asyncio.create_subprocess_exec(
                    *stats_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await stats_process.communicate()
                if stdout:
                    # 解析内存使用量 (格式: "1.5MiB / 128MiB")
                    mem_str = stdout.decode().strip()
                    if "/" in mem_str:
                        used_mem = mem_str.split("/")[0].strip()
                        if "MiB" in used_mem:
                            memory_used = int(float(used_mem.replace("MiB", "")))
                        elif "KiB" in used_mem:
                            memory_used = int(float(used_mem.replace("KiB", "")) / 1024)
            except:
                pass
            
            if memory_used > memory_limit:
                return {
                    "status": "MLE",
                    "time_used": time_used,
                    "memory_used": memory_used
                }
            
            return {
                "status": "AC",
                "time_used": time_used,
                "memory_used": memory_used,
                "output": stdout.decode()
            }
            
        except Exception as e:
            return {"status": "UNK", "error": str(e)}
        finally:
            # 清理资源
            try:
                # 删除镜像
                await asyncio.create_subprocess_exec("docker", "rmi", image_name)
                # 删除Dockerfile
                if os.path.exists(dockerfile_path):
                    os.remove(dockerfile_path)
            except:
                pass
    
    async def judge_test_case(
        self,
        code: str,
        language: str,
        input_data: str,
        expected_output: str,
        time_limit: float,
        memory_limit: int,
        judge_mode: str = "standard",
        problem_id: str = ""
    ):
        """评测单个测试点（Docker版本）"""
        try:
            # 创建临时目录和代码文件
            with tempfile.TemporaryDirectory() as temp_dir:
                # 生成代码文件
                if language == "python":
                    code_file = os.path.join(temp_dir, "main.py")
                elif language == "cpp":
                    code_file = os.path.join(temp_dir, "main.cpp")
                else:
                    return self._create_test_case_result("CE", input_data=input_data, expected_output=expected_output)
                
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                # 生成容器名称
                container_name = f"{self.container_prefix}{uuid.uuid4().hex[:8]}"
                
                # 在Docker中运行
                result = await self.run_in_docker(
                    language, code_file, input_data, time_limit, memory_limit, container_name
                )
                
                # 处理结果
                if result["status"] in ["CE", "TLE", "MLE", "RE", "UNK"]:
                    return self._create_test_case_result(
                        status=result["status"],
                        time_used=result.get("time_used", 0),
                        memory_used=result.get("memory_used", 0),
                        input_data=input_data,
                        expected_output=expected_output,
                        actual_output=result.get("output", "")
                    )
                
                # 比较输出
                actual_output = result["output"].rstrip()
                expected_output = expected_output.rstrip()
                
                # 根据评测模式进行判断
                if judge_mode == "spj" and problem_id:
                    # 使用SPJ脚本进行评测
                    try:
                        from .routers.spj import run_spj_script
                        spj_result = await run_spj_script(problem_id, input_data, expected_output, actual_output)
                        
                        if spj_result.get("status") == "ACCEPTED":
                            return self._create_test_case_result(
                                status="AC",
                                time_used=result["time_used"],
                                memory_used=result["memory_used"],
                                input_data=input_data,
                                expected_output=expected_output,
                                actual_output=actual_output
                            )
                        else:
                            return self._create_test_case_result(
                                status="WA",
                                time_used=result["time_used"],
                                memory_used=result["memory_used"],
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
                        return self._create_test_case_result(
                            status="AC",
                            time_used=result["time_used"],
                            memory_used=result["memory_used"],
                            input_data=input_data,
                            expected_output=expected_output,
                            actual_output=actual_output
                        )
                    else:
                        return self._create_test_case_result(
                            status="WA",
                            time_used=result["time_used"],
                            memory_used=result["memory_used"],
                            input_data=input_data,
                            expected_output=expected_output,
                            actual_output=actual_output
                        )
                else:
                    # 标准模式：忽略多余空格和换行
                    if self._normalize_output(actual_output) == self._normalize_output(expected_output):
                        return self._create_test_case_result(
                            status="AC",
                            time_used=result["time_used"],
                            memory_used=result["memory_used"],
                            input_data=input_data,
                            expected_output=expected_output,
                            actual_output=actual_output
                        )
                    else:
                        return self._create_test_case_result(
                            status="WA",
                            time_used=result["time_used"],
                            memory_used=result["memory_used"],
                            input_data=input_data,
                            expected_output=expected_output,
                            actual_output=actual_output
                        )
                
        except Exception as e:
            print(f"Docker评测错误: {e}")
            return self._create_test_case_result(
                status="UNK",
                input_data=input_data,
                expected_output=expected_output,
                actual_output=""
            )
    
    def _create_test_case_result(self, status: str, time_used: float = 0, memory_used: int = 0, 
                                input_data: str = "", expected_output: str = "", actual_output: str = ""):
        """创建测试用例结果对象"""
        # 创建一个简单的对象，与judge.py中的TestCaseResult兼容
        class TestCaseResult:
            def __init__(self, status: str, time_used: float = 0, memory_used: int = 0, 
                         input_data: str = "", expected_output: str = "", actual_output: str = ""):
                self.status = status
                self.time_used = time_used
                self.memory_used = memory_used
                self.input_data = input_data
                self.expected_output = expected_output
                self.actual_output = actual_output
        
        return TestCaseResult(status, time_used, memory_used, input_data, expected_output, actual_output)
    
    def _normalize_output(self, output: str) -> str:
        """标准化输出，忽略多余的空格和换行"""
        lines = output.split('\n')
        normalized_lines = []
        for line in lines:
            normalized_lines.append(line.rstrip())
        return '\n'.join(normalized_lines).rstrip()
    
    async def _run_simulation(
        self,
        language: str,
        code_file: str,
        input_data: str,
        time_limit: float,
        memory_limit: int
    ) -> Dict[str, Any]:
        """模拟Docker运行（当Docker不可用时）"""
        try:
            start_time = time.time()
            
            # 检查代码安全性
            with open(code_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # 检查危险操作
            dangerous_ops = [
                "import os", "import subprocess", "os.system", "subprocess.call",
                "subprocess.run", "eval(", "exec(", "__import__"
            ]
            
            for op in dangerous_ops:
                if op in code_content:
                    return {
                        "status": "RE",
                        "time_used": 0,
                        "error": f"检测到危险操作: {op}"
                    }
            
            # 模拟运行代码
            if language == "python":
                cmd = ["python", code_file]
            elif language == "cpp":
                # 模拟编译
                compile_cmd = ["g++", "-o", code_file.replace(".cpp", ""), code_file]
                compile_process = await asyncio.create_subprocess_exec(
                    *compile_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await compile_process.communicate()
                if compile_process.returncode != 0:
                    return {"status": "CE", "error": stderr.decode()}
                
                cmd = [code_file.replace(".cpp", "")]
            else:
                return {"status": "CE", "error": f"不支持的语言: {language}"}
            
            # 运行代码
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data.encode()),
                    timeout=time_limit
                )
            except asyncio.TimeoutError:
                process.kill()
                return {"status": "TLE", "time_used": time_limit}
            
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
                return {
                    "status": "MLE",
                    "time_used": time_used,
                    "memory_used": memory_used
                }
            
            if process.returncode != 0:
                return {
                    "status": "RE",
                    "time_used": time_used,
                    "error": stderr.decode()
                }
            
            return {
                "status": "AC",
                "time_used": time_used,
                "memory_used": memory_used,
                "output": stdout.decode()
            }
            
        except Exception as e:
            return {"status": "UNK", "error": str(e)}
    
    async def cleanup_containers(self):
        """清理所有评测容器"""
        if not getattr(self, 'docker_available', True):
            return  # Docker不可用时无需清理
        
        try:
            # 查找并删除所有评测容器
            list_cmd = ["docker", "ps", "-a", "--filter", f"name={self.container_prefix}", "--format", "{{.Names}}"]
            list_process = await asyncio.create_subprocess_exec(
                *list_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await list_process.communicate()
            
            if stdout:
                containers = stdout.decode().strip().split('\n')
                for container in containers:
                    if container.strip():
                        await asyncio.create_subprocess_exec("docker", "rm", "-f", container.strip())
        except Exception as e:
            print(f"清理容器失败: {e}")


# 全局Docker评测器实例
docker_judge = DockerJudge() 