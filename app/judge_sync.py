#!/usr/bin/env python3

import asyncio
from .judge import judge
from .models import data_store


def judge_submission_sync(submission_id: str):   
    try:
        # 运行异步评测并等待完成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(judge.judge_submission(submission_id))
            return result
        finally:
            loop.close()
    except Exception as e:
        print(f"评测错误: {e}")
        return None


def ensure_judge_complete(submission_id: str, max_wait: float = 5.0):   # 确保评测完成
    import time
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        submission = data_store.get_submission(submission_id)
        if submission and submission["status"] in ["success", "error"]:
            return True
        time.sleep(0.1)
    
    return False 