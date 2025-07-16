#!/usr/bin/env python3
import json
import sys

def main():
    data = json.loads(sys.stdin.read())
    input_data = data["input"]
    expected_output = data["expected_output"]
    actual_output = data["actual_output"]
    
    if expected_output.strip() in actual_output.strip():
        result = {"status": "ACCEPTED", "score": 100, "message": "输出正确"}
    else:
        result = {"status": "WRONG_ANSWER", "score": 0, "message": "输出错误"}
    
    print(json.dumps(result))

if __name__ == "__main__":
    main()
