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


# 数据存储类
class DataStore:
    def __init__(self):
        self.users_file = "users.json"
        self.sessions_file = "sessions.json"
        self.users = {}
        self.sessions = {}
        self.load_data()
        self.ensure_admin_exists()
    
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
    
    def save_data(self):
        """保存数据到文件"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
        
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)
    
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
    
    def reset_system(self):
        """重置系统"""
        self.users = {}
        self.sessions = {}
        self.save_data()
        self.ensure_admin_exists()


# 全局数据存储实例
data_store = DataStore() 