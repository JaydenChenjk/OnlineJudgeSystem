#!/usr/bin/env python3
"""
SPJ集成测试运行脚本
启动服务器并运行完整的SPJ功能测试
"""

import subprocess
import time
import sys
import os
import signal
import requests

def wait_for_server(url: str, timeout: int = 30) -> bool:
    """等待服务器启动"""
    print(f"等待服务器启动: {url}")
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                print("✅ 服务器启动成功")
                return True
        except:
            pass
        time.sleep(1)
        print(f"等待中... ({i+1}/{timeout})")
    
    print("❌ 服务器启动超时")
    return False

def run_spj_tests():
    """运行SPJ集成测试"""
    print("=== SPJ集成测试 ===")
    
    # 启动服务器
    print("1. 启动服务器...")
    server_process = subprocess.Popen([
        sys.executable, "-m", "app.main"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # 等待服务器启动
        if not wait_for_server("http://localhost:8000"):
            print("服务器启动失败，退出测试")
            return False
        
        # 运行pytest测试
        print("2. 运行SPJ集成测试...")
        test_result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_spj_integration.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        # 输出测试结果
        print("\n=== 测试输出 ===")
        print(test_result.stdout)
        
        if test_result.stderr:
            print("\n=== 错误输出 ===")
            print(test_result.stderr)
        
        # 检查测试结果
        if test_result.returncode == 0:
            print("\n🎉 SPJ集成测试全部通过！")
            return True
        else:
            print("\n💥 SPJ集成测试失败！")
            return False
            
    finally:
        # 停止服务器
        print("3. 停止服务器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("服务器已停止")

def run_single_test(test_name: str):
    """运行单个测试"""
    print(f"=== 运行单个测试: {test_name} ===")
    
    # 启动服务器
    print("1. 启动服务器...")
    server_process = subprocess.Popen([
        sys.executable, "-m", "app.main"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # 等待服务器启动
        if not wait_for_server("http://localhost:8000"):
            print("服务器启动失败，退出测试")
            return False
        
        # 运行指定测试
        print(f"2. 运行测试: {test_name}...")
        test_result = subprocess.run([
            sys.executable, "-m", "pytest", 
            f"tests/test_spj_integration.py::{test_name}", 
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        # 输出测试结果
        print("\n=== 测试输出 ===")
        print(test_result.stdout)
        
        if test_result.stderr:
            print("\n=== 错误输出 ===")
            print(test_result.stderr)
        
        # 检查测试结果
        if test_result.returncode == 0:
            print(f"\n🎉 测试 {test_name} 通过！")
            return True
        else:
            print(f"\n💥 测试 {test_name} 失败！")
            return False
            
    finally:
        # 停止服务器
        print("3. 停止服务器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("服务器已停止")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 运行指定测试
        test_name = sys.argv[1]
        success = run_single_test(test_name)
    else:
        # 运行所有测试
        success = run_spj_tests()
    
    sys.exit(0 if success else 1) 