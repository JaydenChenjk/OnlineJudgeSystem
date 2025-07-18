#!/usr/bin/env python3
import pytest
import time
import uuid
from fastapi.testclient import TestClient
from app.main import app

class TestSPJIntegration:   # SPJ功能集成测试类
    
    def create_problem(self, session, problem_id, judge_mode="standard"):   # 创建测试题目
        problem_data = {
            "id": problem_id,
            "title": f"SPJ测试题目 - {judge_mode}",
            "description": "计算平面直角坐标系上某点到原点距离",
            "input_description": "两个浮点数，代表某点的x, y坐标",
            "output_description": "该点到原点距离，保留6位小数",
            "samples": [{"input": "3 4", "output": "5.0"}],
            "testcases": [{"input": "3 4", "output": "5.0"}],
            "constraints": "|a|,|b| <= 10^9",
            "time_limit": 1.0,
            "memory_limit": 128,
            "judge_mode": judge_mode
        }
        
        response = session.post("/api/problems/", json=problem_data)
        assert response.status_code == 200
        return response.json()["data"]["id"]
    
    @pytest.fixture
    def admin_session(self):   # 管理员会话
        client = TestClient(app)
        login_data = {"username": "admin", "password": "admintestpassword"}
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200, "管理员登录失败"
        return client
    
    @pytest.fixture
    def user_session(self):   # 普通用户会话
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
    def spj_problem_id(self):   # SPJ测试题目ID
        return f"spj_test_{uuid.uuid4().hex[:8]}"
    
    @pytest.fixture
    def python_spj_script(self):   # Python SPJ脚本
        return '''#!/usr/bin/env python3
import sys
import json

def main():
    try:
        # 从标准输入读取 JSON 格式的输入
        data = json.load(sys.stdin)

        input_data = data.get("input", "").strip()
        expected_output = data.get("expected_output", "").strip()
        actual_output = data.get("actual_output", "").strip()

        # 转为浮点数列表
        try:
            expected = list(map(float, expected_output.split()))
            actual = list(map(float, actual_output.split()))
        except ValueError:
            raise Exception("输出格式错误，无法转换为浮点数")

        # 判断长度是否一致
        if len(expected) != len(actual):
            result = {"status": "WA", "score": 0, "message": "输出长度不一致"}
        else:            
            eps = 1e-5  # 允许误差
            correct = all(abs(e - a) <= eps for e, a in zip(expected, actual))
            if correct:
                result = {"status": "AC", "score": 100, "message": "输出正确"}
            else:
                result = {"status": "WA", "score": 0, "message": "输出值不匹配"}

    except Exception as e:
        result = {"status": "SPJ_ERROR", "score": 0, "message": str(e)}

    print(json.dumps(result))

if __name__ == "__main__":
    main()
'''
    
    def test_1_judge_mode_display(self, admin_session, spj_problem_id):     # 测试1: judge_mode字段设置和显示        
        standard_id = self.create_problem(admin_session, f"{spj_problem_id}_standard", "standard")
        spj_id = self.create_problem(admin_session, f"{spj_problem_id}_spj", "spj")
        
        # 验证judge_mode字段显示
        response = admin_session.get(f"/api/problems/{standard_id}")
        assert response.status_code == 200
        standard_problem = response.json()["data"]
        assert standard_problem["judge_mode"] == "standard"
        
        response = admin_session.get(f"/api/problems/{spj_id}")
        assert response.status_code == 200
        spj_problem = response.json()["data"]
        assert spj_problem["judge_mode"] == "spj"
        assert spj_problem["has_spj"] == False  # 还没有上传SPJ脚本
    
    def test_2_admin_spj_management(self, admin_session, spj_problem_id, python_spj_script):    # 测试2: 管理员SPJ脚本管理
        
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 验证题目状态
        response = admin_session.get(f"/api/problems/{spj_problem_id}")
        assert response.status_code == 200
        problem = response.json()["data"]
        assert problem["has_spj"] == True
        
        cpp_script = '''#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <cmath>
using namespace std;

int main() {
    string input, expected, actual;
    getline(cin, input);
    getline(cin, expected);
    getline(cin, actual);
    
    try {
        // 解析浮点数
        vector<double> expected_nums, actual_nums;
        stringstream ss1(expected), ss2(actual);
        double num;
        
        while (ss1 >> num) expected_nums.push_back(num);
        while (ss2 >> num) actual_nums.push_back(num);
        
        if (expected_nums.size() != actual_nums.size()) {
            cout << "{\\"status\\":\\"WA\\",\\"score\\":0,\\"message\\":\\"输出长度不一致\\"}" << endl;
            return 0;
        }
        
        // 允许误差
        double eps = 1e-5;  
        bool correct = true;
        for (size_t i = 0; i < expected_nums.size(); i++) {
            if (abs(expected_nums[i] - actual_nums[i]) > eps) {
                correct = false;
                break;
            }
        }
        
        if (correct) {
            cout << "{\\"status\\":\\"AC\\",\\"score\\":100,\\"message\\":\\"输出正确\\"}" << endl;
        } else {
            cout << "{\\"status\\":\\"WA\\",\\"score\\":0,\\"message\\":\\"输出值不匹配\\"}" << endl;
        }
    } catch (...) {
        cout << "{\\"status\\":\\"SPJ_ERROR\\",\\"score\\":0,\\"message\\":\\"解析错误\\"}" << endl;
    }
    
    return 0;
}'''
        
        files = {"file": ("spj_script.cpp", cpp_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        response = admin_session.delete(f"/api/problems/{spj_problem_id}/spj")
        assert response.status_code == 200
        
        # 验证题目状态
        response = admin_session.get(f"/api/problems/{spj_problem_id}")
        assert response.status_code == 200
        problem = response.json()["data"]
        assert problem["has_spj"] == False
    
    def test_3_user_permission_denied(self, admin_session, user_session, spj_problem_id, python_spj_script):    # 测试3: 普通用户权限控制   
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        # 普通用户尝试上传SPJ脚本
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = user_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 403  # 权限不足
        
        # 普通用户尝试删除SPJ脚本
        response = user_session.delete(f"/api/problems/{spj_problem_id}/spj")
        assert response.status_code == 403  # 权限不足
    
    def test_4_spj_evaluation(self, admin_session, user_session, spj_problem_id, python_spj_script):    # 测试4: 评测时可以正确调用SPJ脚本运行评测
        
        # 创建SPJ题目并上传脚本
        self.create_problem(admin_session, spj_problem_id, "spj")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 提交浮点数计算代码（应该AC，因为有误差容忍）
        float_code = "import math\na, b = map(float, input().split())\nresult = math.sqrt(a*a + b*b)\nprint(f'{result:.6f}')"
        submission_data = {
            "problem_id": spj_problem_id,
            "language": "python",
            "code": float_code
        }
        
        response = user_session.post("/api/submissions/", json=submission_data)
        assert response.status_code == 200
        submission_id = response.json()["data"]["submission_id"]
        time.sleep(1)
        
        # 查询结果
        response = user_session.get(f"/api/submissions/{submission_id}")
        assert response.status_code == 200
        result = response.json()["data"]
        
        # 提交错误代码（应该WA）
        wrong_code = "a, b = map(float, input().split())\nprint(a + b)"  # 加法而不是平方根
        submission_data["code"] = wrong_code
        
        response = user_session.post("/api/submissions/", json=submission_data)
        assert response.status_code == 200
        wrong_submission_id = response.json()["data"]["submission_id"]
        
        # 等待评测完成
        time.sleep(1)
        
        # 查询结果
        response = user_session.get(f"/api/submissions/{wrong_submission_id}")
        assert response.status_code == 200
        wrong_result = response.json()["data"]
        
        # 验证结果
        assert result["score"] > 0, "正确代码应该得分"
        assert wrong_result["score"] == 0, "错误代码不应得分"
        
        # 清理
        admin_session.delete(f"/api/problems/{spj_problem_id}/spj")
    
    def test_5_security_validation(self, admin_session, spj_problem_id):    # 测试5: 安全验证        
        self.create_problem(admin_session, spj_problem_id, "spj")
        
        # 测试不支持的文件类型
        js_script = "console.log('test');"
        files = {"file": ("spj_script.js", js_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 400  # 不支持的文件类型
        
        # 测试危险脚本内容
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
        
        # 测试正常脚本
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
        
        admin_session.delete(f"/api/problems/{spj_problem_id}/spj")
    
    def test_6_spj_test_interface(self, admin_session, spj_problem_id, python_spj_script):    # 测试6: SPJ脚本测试接口
        self.create_problem(admin_session, spj_problem_id, "spj")
        files = {"file": ("spj_script.py", python_spj_script.encode('utf-8'), "text/plain")}
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj", files=files)
        assert response.status_code == 200
        
        # 测试SPJ脚本执行 - 浮点数比较
        test_data = {
            "input_data": "3 4",
            "expected_output": "5.0",
            "actual_output": "5.000001"  # 有微小误差，但应该在容忍范围内
        }
        
        response = admin_session.post(f"/api/problems/{spj_problem_id}/spj/test", data=test_data)
        assert response.status_code == 200
        test_result = response.json()["data"]
        
        assert test_result["status"] == "AC"
        assert test_result["score"] == 100
        
        admin_session.delete(f"/api/problems/{spj_problem_id}/spj") 