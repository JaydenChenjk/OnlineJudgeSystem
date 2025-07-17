#!/usr/bin/env python3
"""
SPJ功能集成测试
测试SPJ功能的完整流程，包括管理界面、权限控制、脚本执行等
"""

import pytest
import time
import uuid
from fastapi.testclient import TestClient
from app.main import app

class TestSPJIntegration:
    """SPJ功能集成测试类"""
    
    def create_problem(self, session, problem_id, judge_mode="standard"):
        """创建测试题目"""
        problem_data = {
            "id": problem_id,
            "title": f"SPJ测试题目 - {judge_mode}",
            "description": "计算a+b",
            "input_description": "两个整数",
            "output_description": "它们的和",
            "samples": [{"input": "1 2", "output": "3"}],
            "testcases": [{"input": "1 2", "output": "3"}],
            "constraints": "|a|,|b| <= 10^9",
            "time_limit": 1.0,
            "memory_limit": 128,
            "judge_mode": judge_mode
        }
        
        response = session.post("/api/problems/", json=problem_data)
        assert response.status_code == 200
        return response.json()["data"]["id"]
    
    @pytest.fixture
    def admin_session(self):
        """管理员会话"""
        client = TestClient(app)
        # 登录管理员
        login_data = {"username": "admin", "password": "admintestpassword"}
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200, "管理员登录失败"
        return client
    
    @pytest.fixture
    def user_session(self):
        """普通用户会话"""
        # 用admin注册用户
        admin_client = TestClient(app)
        admin_client.post("/api/auth/login", json={"username": "admin", "password": "admintestpassword"})
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "testpass123"
        admin_client.post("/api/users/", json={"username": username, "password": password})
        # 用户独立会话
        client = TestClient(app)
        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, "用户登录失败"
        return client
    
    @pytest.fixture
    def spj_problem_id(self):
        """SPJ测试题目ID"""
        return f"spj_test_{uuid.uuid4().hex[:8]}"
    
    @pytest.fixture
    def python_spj_script(self):
        """Python SPJ脚本"""
        return '''#!/usr/bin/env python3
import json
import sys

def main():
    data = json.loads(sys.stdin.read())
    input_data = data["input"]
    expected_output = data["expected_output"]
    actual_output = data["actual_output"]
    
    # 简单的SPJ逻辑：检查输出是否包含期望的结果
    if expected_output.strip() in actual_output.strip():
        result = {"status": "ACCEPTED", "score": 100, "message": "输出正确"}
    else:
        result = {"status": "WRONG_ANSWER", "score": 0, "message": "输出错误"}
    
    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
    
    def test_1_judge_mode_display(self, admin_session, spj_problem_id):
        """测试1: judge_mode字段设置和显示"""
        print("\n=== 测试1: judge_mode字段设置和显示 ===")
        
        # 1.1 创建标准模式题目
        standard_id = self.create_problem(admin_session, f"{spj_problem_id}_standard", "standard")
        print("✅ 标准模式题目创建成功")
        
        # 1.2 创建SPJ模式题目
        spj_id = self.create_problem(admin_session, f"{spj_problem_id}_spj", "spj")
        print("✅ SPJ模式题目创建成功")
        
        # 1.3 验证judge_mode字段显示
        response = admin_session.get(f"/api/problems/{standard_id}")
        assert response.status_code == 200
        standard_problem = response.json()["data"]
        assert standard_problem["judge_mode"] == "standard"
        
        response = admin_session.get(f"/api/problems/{spj_id}")
        assert response.status_code == 200
        spj_problem = response.json()["data"]
        assert spj_problem["judge_mode"] == "spj"
        assert spj_problem["has_spj"] == False  # 还没有上传SPJ脚本
        
        print("✅ judge_mode字段正确显示")
    
    def test_2_admin_spj_management(self, admin_session, spj_problem_id, python_spj_script):
        """测试2: 管理员SPJ脚本管理"""
        print("\n=== 测试2: 管理员SPJ脚本管理 ===")
        
        # 2.1 上传Python SPJ脚本
        print("2.1 上传Python SPJ脚本...")
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        print("✅ Python SPJ脚本上传成功")
        
        # 验证题目状态
        response = admin_session.get(f"/api/problems/{spj_problem_id}")
        assert response.status_code == 200
        problem = response.json()["data"]
        assert problem["has_spj"] == True
        print("✅ 题目状态正确显示有SPJ")
        
        # 2.2 更新为C++ SPJ脚本
        print("2.2 更新为C++ SPJ脚本...")
        cpp_script = '''#include <iostream>
#include <string>
using namespace std;

int main() {
    string input, expected, actual;
    getline(cin, input);
    getline(cin, expected);
    getline(cin, actual);
    
    if (actual.find(expected) != string::npos) {
        cout << "{\\"status\\":\\"ACCEPTED\\",\\"score\\":100,\\"message\\":\\"输出正确\\"}" << endl;
    } else {
        cout << "{\\"status\\":\\"WRONG_ANSWER\\",\\"score\\":0,\\"message\\":\\"输出错误\\"}" << endl;
    }
    return 0;
}'''
        
        files = {"file": ("spj_script.cpp", cpp_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        print("✅ C++ SPJ脚本更新成功")
        
        # 2.3 删除SPJ脚本
        print("2.3 删除SPJ脚本...")
        response = admin_session.delete(f"/api/problems/{spj_problem_id}/spj")
        assert response.status_code == 200
        print("✅ SPJ脚本删除成功")
        
        # 验证题目状态
        response = admin_session.get(f"/api/problems/{spj_problem_id}")
        assert response.status_code == 200
        problem = response.json()["data"]
        assert problem["has_spj"] == False
        print("✅ 题目状态正确显示无SPJ")
    
    def test_3_user_permission_denied(self, admin_session, user_session, spj_problem_id, python_spj_script):
        """测试3: 普通用户权限控制"""
        print("\n=== 测试3: 普通用户权限控制 ===")
        
        # 创建SPJ题目
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        # 3.1 普通用户尝试上传SPJ脚本
        print("3.1 普通用户尝试上传SPJ脚本...")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = user_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 403  # 权限不足
        print("✅ 正确拒绝普通用户上传SPJ")
        
        # 3.2 普通用户尝试删除SPJ脚本
        print("3.2 普通用户尝试删除SPJ脚本...")
        response = user_session.delete(f"/api/problems/{spj_problem_id}/spj")
        assert response.status_code == 403  # 权限不足
        print("✅ 正确拒绝普通用户删除SPJ")
    
    def test_4_spj_evaluation(self, admin_session, user_session, spj_problem_id, python_spj_script):
        """测试4: 评测时可以正确调用SPJ脚本运行评测"""
        print("\n=== 测试4: SPJ脚本评测 ===")
        
        # 管理员创建SPJ题目并上传脚本
        self.create_problem(admin_session, spj_problem_id, "spj")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 4.1 提交正确代码（应该AC）
        print("4.1 提交正确代码...")
        correct_code = "a, b = map(int, input().split())\nprint(a + b)"
        submission_data = {
            "problem_id": spj_problem_id,
            "language": "python",
            "code": correct_code
        }
        
        response = user_session.post("/api/submissions/", json=submission_data)
        assert response.status_code == 200
        submission_id = response.json()["data"]["submission_id"]
        print(f"✅ 正确代码提交成功，ID: {submission_id}")
        
        # 等待评测完成（TestClient环境下同步评测）
        time.sleep(1)
        
        # 查询结果
        response = user_session.get(f"/api/submissions/{submission_id}")
        assert response.status_code == 200
        result = response.json()["data"]
        print(f"正确代码评测结果: {result['status']}, 得分: {result['score']}")
        
        # 4.2 提交错误代码（应该WA）
        print("4.2 提交错误代码...")
        wrong_code = "a, b = map(int, input().split())\nprint(a - b)"  # 减法而不是加法
        submission_data["code"] = wrong_code
        
        response = user_session.post("/api/submissions/", json=submission_data)
        assert response.status_code == 200
        wrong_submission_id = response.json()["data"]["submission_id"]
        print(f"✅ 错误代码提交成功，ID: {wrong_submission_id}")
        
        # 等待评测完成
        time.sleep(1)
        
        # 查询结果
        response = user_session.get(f"/api/submissions/{wrong_submission_id}")
        assert response.status_code == 200
        wrong_result = response.json()["data"]
        print(f"错误代码评测结果: {wrong_result['status']}, 得分: {wrong_result['score']}")
        
        # 验证结果
        assert result["score"] > 0, "正确代码应该得分"
        assert wrong_result["score"] == 0, "错误代码不应得分"
        print("✅ SPJ评测流程通过")
        
        # 清理
        admin_session.delete(f"/api/problems/{spj_problem_id}/spj")
    
    def test_5_security_validation(self, admin_session, spj_problem_id):
        """测试5: 安全验证"""
        print("\n=== 测试5: 安全验证 ===")
        
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        # 5.1 测试不支持的文件类型
        print("5.1 测试不支持的文件类型...")
        js_script = "console.log('test');"
        files = {"file": ("spj_script.js", js_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 400  # 不支持的文件类型
        print("✅ 正确拒绝.js文件")
        
        # 5.2 测试危险脚本内容
        print("5.2 测试危险脚本内容...")
        dangerous_scripts = [
            ("eval('print(1)')", "危险脚本 1"),
            ("exec('import os')", "危险脚本 2"),
            ("os.system('ls')", "危险脚本 3"),
            ("subprocess.call(['ls'])", "危险脚本 4"),
            ("subprocess.run(['ls'])", "危险脚本 5")
        ]
        
        for script, name in dangerous_scripts:
            files = {"file": ("spj_script.py", script.encode('utf-8'), "text/plain")}
            response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
            assert response.status_code == 400  # 危险内容被拒绝
            print(f"✅ 正确拒绝{name}")
        
        # 5.3 测试正常脚本
        print("5.3 测试正常脚本...")
        normal_script = '''#!/usr/bin/env python3
import json
import sys

def main():
    data = json.loads(sys.stdin.read())
    print(json.dumps({"status": "AC", "score": 100}))

if __name__ == "__main__":
    main()
'''
        files = {"file": ("spj_script.py", normal_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200  # 正常脚本通过
        print("✅ 正常脚本通过验证")
        
        # 清理
        admin_session.delete(f"/api/problems/{spj_problem_id}/spj")
    
    def test_6_spj_test_interface(self, admin_session, spj_problem_id, python_spj_script):
        """测试6: SPJ脚本测试接口"""
        print("\n=== 测试6: SPJ脚本测试接口 ===")
        
        # 创建题目并上传SPJ脚本
        self.create_problem(admin_session, spj_problem_id, "spj")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 6.1 测试SPJ脚本执行
        print("6.1 测试SPJ脚本执行...")
        test_data = {
            "input_data": "1 2",
            "expected_output": "3",
            "actual_output": "3"
        }
        
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj/test", data=test_data)
        assert response.status_code == 200
        test_result = response.json()["data"]
        print(f"SPJ测试结果: {test_result}")
        
        assert test_result["status"] == "AC"
        assert test_result["score"] == 100
        print("✅ SPJ脚本测试接口正常")
        
        # 清理
        admin_session.delete(f"/api/problems/{spj_problem_id}/spj") 