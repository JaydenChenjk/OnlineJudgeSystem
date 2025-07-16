# SPJ API接口实现说明

## 题目要求的API接口

根据题目要求，SPJ功能需要实现以下API接口：

### 1. 上传SPJ脚本
- **接口**: `POST /api/problems/{problem_id}/spj`
- **参数**: 
  - `file` (file, 必填): SPJ脚本文件
- **权限**: 仅管理员
- **功能**: 上传指定题目的SPJ脚本

### 2. 删除SPJ脚本
- **接口**: `DELETE /api/problems/{problem_id}/spj`
- **参数**: 无
- **权限**: 仅管理员
- **功能**: 删除指定题目的SPJ脚本

### 3. 查询题目评测策略
- **接口**: `GET /api/problems/{problem_id}`
- **参数**: 无
- **权限**: 需要登录
- **功能**: 查询题目详情，包含SPJ脚本状态

## 实现细节

### 文件结构
```
app/
├── routers/
│   ├── problems.py    # 题目相关接口，包含SPJ状态查询
│   └── spj.py         # SPJ脚本管理接口
└── main.py            # 主应用，注册路由
```

### 路由注册
- SPJ路由使用前缀 `/api/problems`，这样SPJ接口的完整路径为：
  - `POST /api/problems/{problem_id}/spj`
  - `DELETE /api/problems/{problem_id}/spj`
  - `GET /api/problems/{problem_id}/spj` (获取SPJ脚本内容)
  - `POST /api/problems/{problem_id}/spj/test` (测试SPJ脚本)

### 功能特性

#### 1. 文件类型支持
- 支持 `.py` (Python) 和 `.cpp` (C++) 文件
- 自动检测文件扩展名并相应处理

#### 2. 安全验证
- 检查脚本内容是否包含危险函数（如 `eval`, `exec`, `os.system` 等）
- 防止恶意代码执行

#### 3. 脚本执行
- **Python脚本**: 直接执行，使用JSON格式输入输出
- **C++脚本**: 先编译后执行，使用简单文本格式输入输出

#### 4. 题目状态集成
- 在题目详情接口中返回 `has_spj` 字段，表示是否有SPJ脚本
- 实时反映SPJ脚本的上传/删除状态

### 测试验证

运行 `test_spj_api.py` 可以验证所有功能：

1. ✅ 管理员登录
2. ✅ 创建测试题目
3. ✅ 查询题目详情（显示无SPJ）
4. ✅ 上传SPJ脚本
5. ✅ 再次查询题目详情（显示有SPJ）
6. ✅ 测试SPJ脚本执行
7. ✅ 删除SPJ脚本
8. ✅ 最终查询题目详情（显示无SPJ）
9. ✅ 删除测试题目

### API响应格式

所有接口都遵循统一的响应格式：
```json
{
  "code": 200,
  "msg": "success",
  "data": {...}
}
```

### 错误处理

- 400: 参数错误（如不支持的文件类型、危险代码等）
- 404: 资源不存在（如题目不存在、SPJ脚本不存在等）
- 500: 服务器内部错误

## 总结

SPJ API接口已完全按照题目要求实现：
- ✅ 路径格式正确：`/api/problems/{problem_id}/spj`
- ✅ 支持文件上传和删除
- ✅ 题目查询接口包含SPJ状态信息
- ✅ 权限控制正确（仅管理员可管理SPJ）
- ✅ 功能完整且经过测试验证 