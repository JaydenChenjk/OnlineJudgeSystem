# by Hidrogen_Peroxide 7/15 20:04
# upload 和 delete 对接口是否能正确返回200状态码进行了检测
# test_spj_submission函数使用.py文件格式特判

# 如果没有spj但使用spj评测(?)
# pytest tests/mytest_adv1.py
from test_helpers import setup_admin_session, reset_system, setup_user_session
import uuid
import time

# pytest tests/mytest_adv1.py -k test_upload_spj -v
def test_upload_spj(client):
    reset_system(client)
    setup_admin_session(client)
    problem_id = "test_list_" + uuid.uuid4().hex[:4]
    problem_data = {
        "id": problem_id,
        "title": "测试列表",
        "description": "计算a+b",
        "input_description": "两个整数",
        "output_description": "它们的和",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "testcases": [{"input": "1 2\n", "output": "3\n"}],
        "constraints": "|a|,|b| <= 10^9",
        "time_limit": 1.0,
        "memory_limit": 128,
        "judge_mode": "spj",
    }
    client.post("/api/problems/", json=problem_data)
    spj_file_content = 'print("SPJ script")'
    spj_response = client.post(f"/api/spj/upload/{problem_id}", files={"file": ("spj.py", spj_file_content)})
    print("spj_response.text:", spj_response.text)
    assert spj_response.status_code == 200

# pytest tests/mytest_adv1.py -k test_delete_spj -v
def test_delete_spj(client):
    reset_system(client)
    setup_admin_session(client)
    problem_id = "test_list_" + uuid.uuid4().hex[:4]
    problem_data = {
        "id": problem_id,
        "title": "测试列表",
        "description": "计算a+b",
        "input_description": "两个整数",
        "output_description": "它们的和",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "testcases": [{"input": "1 2\n", "output": "3\n"}],
        "constraints": "|a|,|b| <= 10^9",
        "time_limit": 1.0,
        "memory_limit": 128,
        "judge_mode": "spj",
    }
    client.post("/api/problems/", json=problem_data)
    spj_file_content = 'print("SPJ script")'
    client.post(f"/api/spj/upload/{problem_id}", files={"file": ("spj.py", spj_file_content)})
    spj_response = client.delete(f"/api/spj/{problem_id}")
    assert spj_response.status_code == 200

# pytest tests/mytest_adv1.py -k test_spj_submission_python -v -s
def test_spj_submission_python(client):
    reset_system(client)
    setup_admin_session(client)
    problem_id = "test_list_" + uuid.uuid4().hex[:4]
    problem_data = {
        "id": problem_id,
        "title": "测试列表",
        "description": "计算a+b",
        "input_description": "两个整数",
        "output_description": "它们的和",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "testcases": [{"input": "1 2\n", "output": "3\n"}],
        "constraints": "|a|,|b| <= 10^9",
        "time_limit": 1.0,
        "memory_limit": 128,
        "judge_mode": "spj",
    }
    client.post("/api/problems/", json=problem_data)
    spj_file_content = (
        'import sys\n'
        'def main():\n'
        '    if len(sys.argv) != 3:\n'
        '        print("Usage: spj.py std_output user_output", file=sys.stderr)\n'
        '        sys.exit(3)\n'
        '    std_path = sys.argv[1]\n'
        '    user_path = sys.argv[2]\n'
        '    try:\n'
        '        with open(std_path, "r") as f_std, open(user_path, "r") as f_user:\n'
        '            for std_line in f_std:\n'
        '                user_line = f_user.readline()\n'
        '                if user_line == "":\n'
        '                    sys.exit(1)\n'
        '                if std_line.rstrip() != user_line.rstrip():\n'
        '                    sys.exit(1)\n'
        '            if f_user.readline() != "":\n'
        '                sys.exit(1)\n'
        '    except Exception as e:\n'
        '        print(f"Cannot open output files: {e}", file=sys.stderr)\n'
        '        sys.exit(3)\n'
        '    sys.exit(0)\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    client.post(f"/api/spj/upload/{problem_id}", files={"file": ("spj.py", spj_file_content)})
    submission_data = {
        "problem_id": problem_id,
        "language": "python",
        "code": "a, b = map(int, input().split())\nprint(a+b)\n"
    }
    submit_response = client.post("/api/submissions/", json=submission_data)
    assert submit_response.status_code == 200
    time.sleep(2)
    submission_id = submit_response.json()["data"]["submission_id"]
    log_response = client.get(f"/api/submissions/{submission_id}/log")
    assert log_response.status_code == 200
    log_data = log_response.json()["data"]
    print("log_data:", log_data)
    print("full log response:", log_response.json())
    assert log_data["score"] == 10  # 应该得满分