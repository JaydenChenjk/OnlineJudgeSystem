# 在线评测系统 实验报告

## 一、系统功能与设计

### 1. 核心实现架构与模块划分

#### models.py

- `class DataStore`：**核心数据管理模块**，负责所有用户信息、题目信息、提交记录、语言配置、访问日志等数据的存储与访问，将所有数据保存在 JSON 文件中，并提供统一的操作接口。





### 2. 测试文件逻辑

#### test_docker_security.py

- test_docker_availability：检查 Docker 是否可用
- test_command_validation：测试命令过滤与安全校验
- test_dockerfile_creation：测试Dockerfile创建功能正常
- test_docker_sandbox_isolation：测试Docker沙箱隔离性
- test_memory_time_limits：测试内存和时间限制
- test_security_restrictions：测试网络访问限制
- test_malicious_code_prevention：测试恶意代码防护
- test_normal_code_execution：测试正常C++和Python代码执行
- test_input_output_handling：检查代码能正确处理标准输入与多行输入
- test_judge_test_case_integration：测试完整的评测集成
- test_cleanup_containers：测试清理函数

#### spy_integration_test.py

- test_1_judge_mode_display：测试题目的评测模式字段显示是否正确
- test_2_admin_spj_management：测试管理员上传、替换、删除 SPJ 脚本功能
- test_3_user_permission_denied：验证普通用户无法上传或删除 SPJ 脚本
- test_4_spj_evaluation：测试提交代码时是否正确调用 SPJ 评测
- test_5_security_validation：验证脚本上传时文件类型与内容安全性
- test_6_spj_test_interface：测试 SPJ 测试接口能否执行并返回正确结果  