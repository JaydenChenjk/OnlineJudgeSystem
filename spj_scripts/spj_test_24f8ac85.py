#!/usr/bin/env python3
import json
import sys

def judge(input_data, expected_output, actual_output):
    """SPJ脚本：检查输出是否满足条件"""
    try:
        # 解析输入
        n = int(input_data.strip())
        
        # 解析用户输出
        lines = actual_output.strip().split('\n')
        if len(lines) == 0:
            return {"status": "WA", "message": "输出为空"}
        
        parts = lines[0].strip().split()
        if len(parts) != 2:
            return {"status": "WA", "message": "输出格式错误，需要两个整数"}
        
        try:
            a, b = int(parts[0]), int(parts[1])
        except ValueError:
            return {"status": "WA", "message": "输出不是整数"}
        
        # 检查条件：a + b = n
        if a + b == n:
            return {"status": "AC", "message": "答案正确"}
        else:
            return {"status": "WA", "message": f"答案错误：{a} + {b} != {n}"}
    
    except Exception as e:
        return {"status": "SPJ_ERROR", "message": f"SPJ脚本执行错误: {str(e)}"}

if __name__ == "__main__":
    # 从标准输入读取数据
    input_json = sys.stdin.read()
    data = json.loads(input_json)
    
    # 执行评测
    result = judge(data["input"], data["expected_output"], data["actual_output"])
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False))
