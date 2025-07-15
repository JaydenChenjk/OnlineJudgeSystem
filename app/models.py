import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import bcrypt
import uuid


class Sample(BaseModel):
    input: str
    output: str


class TestCase(BaseModel):
    input: str
    output: str


class Problem(BaseModel):
    id: str = Field(..., description="题目唯一标识")
    title: str = Field(..., description="题目标题")
    description: str = Field(..., description="题目描述")
    input_description: str = Field(..., description="输入格式说明")
    output_description: str = Field(..., description="输出格式说明")
    samples: List[Sample] = Field(..., description="样例输入输出")
    constraints: str = Field(..., description="数据范围和限制条件")
    testcases: List[TestCase] = Field(..., description="测试点")
    hint: Optional[str] = Field("", description="额外提示")
    source: Optional[str] = Field("", description="题目来源或出处")
    tags: Optional[List[str]] = Field([], description="题目标签")
    time_limit: Optional[float] = Field(3.0, description="时间限制")
    memory_limit: Optional[int] = Field(128, description="内存限制")
    author: Optional[str] = Field("", description="题目作者")
    difficulty: Optional[str] = Field("", description="难度等级")
    judge_mode: Optional[str] = Field("standard", description="评测模式：standard(标准), strict(严格), spj(特判)")
    spj_script: Optional[str] = Field("", description="特判脚本内容")


class ProblemSummary(BaseModel):
    id: str
    title: str


class User(BaseModel):
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    password_hash: str = Field(..., description="密码哈希")
    role: str = Field("user", description="用户角色")
    join_time: str = Field(..., description="注册时间")
    submit_count: int = Field(0, description="提交次数")
    resolve_count: int = Field(0, description="解决题目数")


class UserCreate(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserLogin(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="新角色")


class UserInfo(BaseModel):
    user_id: str
    username: str
    role: str
    join_time: str
    submit_count: int
    resolve_count: int


class UserListResponse(BaseModel):
    total: int
    users: List[UserInfo]


class Language(BaseModel):
    name: str = Field(..., description="语言名称")
    file_ext: str = Field(..., description="文件扩展名")
    compile_cmd: Optional[str] = Field("", description="编译命令")
    run_cmd: str = Field(..., description="运行命令")
    time_limit: Optional[float] = Field(3.0, description="默认时间限制")
    memory_limit: Optional[int] = Field(128, description="默认内存限制")


class Submission(BaseModel):
    submission_id: str = Field(..., description="提交ID")
    user_id: str = Field(..., description="用户ID")
    problem_id: str = Field(..., description="题目ID")
    language: str = Field(..., description="编程语言")
    code: str = Field(..., description="代码")
    status: str = Field("pending", description="评测状态")
    score: int = Field(0, description="得分")
    counts: int = Field(0, description="总分")
    submit_time: str = Field(..., description="提交时间")


class SubmissionCreate(BaseModel):
    problem_id: str = Field(..., description="题目ID")
    language: str = Field(..., description="编程语言")
    code: str = Field(..., description="代码")


class TestCaseResult(BaseModel):
    test_case_id: int = Field(..., description="测试用例ID")
    status: str = Field(..., description="评测状态")
    time_used: float = Field(0, description="运行时间")
    memory_used: int = Field(0, description="内存使用")
    input_data: str = Field(..., description="输入数据")
    expected_output: str = Field(..., description="期望输出")
    actual_output: str = Field("", description="实际输出")


class SubmissionLog(BaseModel):
    submission_id: str = Field(..., description="提交ID")
    user_id: str = Field(..., description="用户ID")
    problem_id: str = Field(..., description="题目ID")
    language: str = Field(..., description="编程语言")
    code: str = Field(..., description="代码")
    score: int = Field(0, description="得分")
    counts: int = Field(0, description="总分")
    test_cases: List[TestCaseResult] = Field(..., description="测试用例结果")
    submit_time: str = Field(..., description="提交时间")


class LogVisibilityConfig(BaseModel):
    public_cases: bool = Field(False, description="是否允许公开测试用例")


class AccessLog(BaseModel):
    log_id: str = Field(..., description="访问日志ID")
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    action: str = Field(..., description="操作类型")
    resource_id: str = Field(..., description="资源ID")
    resource_type: str = Field(..., description="资源类型")
    access_time: str = Field(..., description="访问时间")
    ip_address: str = Field("", description="IP地址")


# 数据存储类
class DataStore:
    def __init__(self):
        self.users_file = "users.json"
        self.sessions_file = "sessions.json"
        self.languages_file = "languages.json"
        self.submissions_file = "submissions.json"
        self.submission_logs_file = "submission_logs.json"
        self.problem_visibility_file = "problem_visibility.json"
        self.access_logs_file = "access_logs.json"
        self.users = {}
        self.sessions = {}
        self.languages = {}
        self.submissions = {}
        self.submission_logs = {}
        self.problem_visibility = {}
        self.access_logs = {}
        self.load_data()
        self.ensure_admin_exists()
        self.ensure_default_languages()
    
    def load_data(self):
        """从文件加载数据"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except:
                self.users = {}
        
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    self.sessions = json.load(f)
            except:
                self.sessions = {}
        
        if os.path.exists(self.languages_file):
            try:
                with open(self.languages_file, 'r', encoding='utf-8') as f:
                    self.languages = json.load(f)
            except:
                self.languages = {}
        
        if os.path.exists(self.submissions_file):
            try:
                with open(self.submissions_file, 'r', encoding='utf-8') as f:
                    self.submissions = json.load(f)
            except:
                self.submissions = {}
        
        if os.path.exists(self.submission_logs_file):
            try:
                with open(self.submission_logs_file, 'r', encoding='utf-8') as f:
                    self.submission_logs = json.load(f)
            except:
                self.submission_logs = {}
        
        if os.path.exists(self.problem_visibility_file):
            try:
                with open(self.problem_visibility_file, 'r', encoding='utf-8') as f:
                    self.problem_visibility = json.load(f)
            except:
                self.problem_visibility = {}
        
        if os.path.exists(self.access_logs_file):
            try:
                with open(self.access_logs_file, 'r', encoding='utf-8') as f:
                    self.access_logs = json.load(f)
            except:
                self.access_logs = {}
    
    def save_data(self):
        """保存数据到文件"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
        
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)
        
        with open(self.languages_file, 'w', encoding='utf-8') as f:
            json.dump(self.languages, f, ensure_ascii=False, indent=2)
        
        with open(self.submissions_file, 'w', encoding='utf-8') as f:
            json.dump(self.submissions, f, ensure_ascii=False, indent=2)
        
        with open(self.submission_logs_file, 'w', encoding='utf-8') as f:
            json.dump(self.submission_logs, f, ensure_ascii=False, indent=2)
        
        with open(self.problem_visibility_file, 'w', encoding='utf-8') as f:
            json.dump(self.problem_visibility, f, ensure_ascii=False, indent=2)
        
        with open(self.access_logs_file, 'w', encoding='utf-8') as f:
            json.dump(self.access_logs, f, ensure_ascii=False, indent=2)
    
    def ensure_admin_exists(self):
        """确保管理员账户存在"""
        admin_exists = any(user.get("username") == "admin" for user in self.users.values())
        if not admin_exists:
            admin_id = str(uuid.uuid4())
            password_hash = bcrypt.hashpw("admintestpassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            now = datetime.now().strftime("%Y-%m-%d")
            
            self.users[admin_id] = {
                "user_id": admin_id,
                "username": "admin",
                "password_hash": password_hash,
                "role": "admin",
                "join_time": now,
                "submit_count": 0,
                "resolve_count": 0
            }
            self.save_data()
    
    def ensure_default_languages(self):
        """确保默认语言存在"""
        if "python" not in self.languages:
            self.languages["python"] = {
                "name": "python",
                "file_ext": ".py",
                "compile_cmd": "",
                "run_cmd": "python main.py",
                "time_limit": 3.0,
                "memory_limit": 128
            }
            self.save_data()
    
    def create_user(self, username: str, password: str, role: str = "user") -> str:
        """创建新用户"""
        # 检查用户名是否已存在
        if any(user.get("username") == username for user in self.users.values()):
            raise ValueError("用户名已存在")
        
        # 验证用户名长度
        if len(username) < 3 or len(username) > 40:
            raise ValueError("用户名长度必须在3-40字符之间")
        
        # 验证密码长度
        if len(password) < 6:
            raise ValueError("密码长度至少6位")
        
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.now().strftime("%Y-%m-%d")
        
        self.users[user_id] = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "join_time": now,
            "submit_count": 0,
            "resolve_count": 0
        }
        self.save_data()
        return user_id
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """验证用户登录"""
        for user in self.users.values():
            if user["username"] == username:
                if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
                    if user["role"] == "banned":
                        return None  # 被禁用的用户无法登录
                    return user
                break
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """根据ID获取用户"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户"""
        for user in self.users.values():
            if user["username"] == username:
                return user
        return None
    
    def update_user_role(self, user_id: str, new_role: str):
        """更新用户角色"""
        if user_id not in self.users:
            raise ValueError("用户不存在")
        
        valid_roles = ["user", "admin", "banned"]
        if new_role not in valid_roles:
            raise ValueError("无效的角色")
        
        self.users[user_id]["role"] = new_role
        self.save_data()
    
    def get_all_users(self, page: int = 1, page_size: int = 10) -> dict:
        """获取用户列表"""
        all_users = list(self.users.values())
        total = len(all_users)
        
        start = (page - 1) * page_size
        end = start + page_size
        users_page = all_users[start:end]
        
        return {
            "total": total,
            "users": users_page
        }
    
    def create_session(self, user_id: str) -> str:
        """创建会话"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        self.save_data()
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.save_data()
    
    def register_language(self, language_data: dict):
        """注册新语言"""
        name = language_data["name"]
        if name in self.languages:
            raise ValueError("语言已存在")
        
        self.languages[name] = language_data
        self.save_data()
    
    def get_languages(self) -> dict:
        """获取所有语言"""
        return {"name": list(self.languages.keys())}
    
    def get_language(self, name: str) -> Optional[dict]:
        """获取指定语言"""
        return self.languages.get(name)
    
    def create_submission(self, user_id: str, problem_id: str, language: str, code: str) -> str:
        """创建提交"""
        submission_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        self.submissions[submission_id] = {
            "submission_id": submission_id,
            "user_id": user_id,
            "problem_id": problem_id,
            "language": language,
            "code": code,
            "status": "pending",
            "score": 0,
            "counts": 0,
            "submit_time": now
        }
        
        # 更新用户提交次数
        if user_id in self.users:
            self.users[user_id]["submit_count"] += 1
        
        self.save_data()
        return submission_id
    
    def get_submission(self, submission_id: str) -> Optional[dict]:
        """获取提交信息"""
        return self.submissions.get(submission_id)
    
    def update_submission(self, submission_id: str, **kwargs):
        """更新提交信息"""
        if submission_id in self.submissions:
            self.submissions[submission_id].update(kwargs)
            self.save_data()
    
    def get_submissions(self, user_id: Optional[str] = None, problem_id: Optional[str] = None, judge_status: Optional[str] = None, page: int = 1, page_size: int = 10) -> dict:
        """获取提交列表"""
        all_submissions = list(self.submissions.values())
        
        # 过滤
        if user_id:
            all_submissions = [s for s in all_submissions if s["user_id"] == user_id]
        if problem_id:
            all_submissions = [s for s in all_submissions if s["problem_id"] == problem_id]
        if judge_status:
            all_submissions = [s for s in all_submissions if s["status"] == judge_status]
        
        total = len(all_submissions)
        start = (page - 1) * page_size
        end = start + page_size
        submissions_page = all_submissions[start:end]
        
        return {
            "total": total,
            "submissions": submissions_page
        }
    
    def save_submission_log(self, submission_id: str, log_data: dict):
        """保存提交日志"""
        self.submission_logs[submission_id] = log_data
        self.save_data()
    
    def get_submission_log(self, submission_id: str) -> Optional[dict]:
        """获取提交日志"""
        return self.submission_logs.get(submission_id)
    
    def set_problem_visibility(self, problem_id: str, public_cases: bool):
        """设置题目日志可见性"""
        self.problem_visibility[problem_id] = {"public_cases": public_cases}
        self.save_data()
    
    def get_problem_visibility(self, problem_id: str) -> dict:
        """获取题目日志可见性"""
        return self.problem_visibility.get(problem_id, {"public_cases": False})
    
    def log_access(self, user_id: str, username: str, action: str, resource_id: str, resource_type: str, ip_address: str = ""):
        """记录访问日志"""
        log_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        self.access_logs[log_id] = {
            "log_id": log_id,
            "user_id": user_id,
            "username": username,
            "action": action,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "access_time": now,
            "ip_address": ip_address
        }
        self.save_data()
    
    def get_access_logs(self, user_id: Optional[str] = None, problem_id: Optional[str] = None, page: int = 1, page_size: int = 10) -> dict:
        """获取访问日志"""
        all_logs = list(self.access_logs.values())
        
        # 过滤
        if user_id:
            all_logs = [log for log in all_logs if log["user_id"] == user_id]
        if problem_id:
            all_logs = [log for log in all_logs if log["resource_type"] == "problem" and log["resource_id"] == problem_id]
        
        total = len(all_logs)
        start = (page - 1) * page_size
        end = start + page_size
        logs_page = all_logs[start:end]
        
        return {
            "total": total,
            "logs": logs_page
        }
    
    def reset_system(self):
        """重置系统"""
        self.users = {}
        self.sessions = {}
        self.languages = {}
        self.submissions = {}
        self.submission_logs = {}
        self.problem_visibility = {}
        self.access_logs = {}
        self.save_data()
        self.ensure_admin_exists()
        self.ensure_default_languages()


# 全局数据存储实例
data_store = DataStore() 