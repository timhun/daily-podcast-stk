# grok_api.py - 向後兼容接口，實際使用 nim_api.py
# 為了保持與現有程式碼的相容性
from nim_api import optimize_script_with_grok as _optimize_script_with_grok

def optimize_script_with_grok(initial_script, api_key, model="grok-4", max_retries=3):
    """向後兼容接口"""
    return _optimize_script_with_grok(initial_script, task_type="script")

# 保留原功能作為參考
def _original_grok_api():
    """此函數已停用，功能已整合到 nim_api.py"""