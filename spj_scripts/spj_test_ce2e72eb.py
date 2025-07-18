#!/usr/bin/env python3
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
            # 允许误差
            eps = 1e-5  # 稍微放宽误差容忍
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
