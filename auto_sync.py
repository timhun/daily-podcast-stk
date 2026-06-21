#!/usr/bin/env python3
"""
auto_sync.py - 自動同步 daily-podcast-stk 到 GitHub
功能：每 5 分鐘檢查一次，有變更就自動 commit & push 到 GitHub
"""

import subprocess
import os
import sys
import fcntl
import time
from datetime import datetime

REPO_DIR = "/home/bbm/podcast"
LOCK_FILE = "/tmp/podcast-sync.lock"
LOG_FILE = "/home/bbm/.local/podcast-sync.log"


def log(msg):
    """寫入 log"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)  # 給 cron redirect 用
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run(cmd):
    """執行 shell 命令，回傳 (returncode, stdout, stderr)"""
    result = subprocess.run(
        cmd, shell=True, cwd=REPO_DIR,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def acquire_lock():
    """取得程序鎖，防止多重執行"""
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        return lock_fd
    except (IOError, OSError):
        lock_fd.close()
        return None


def check_changes():
    """檢查是否有未提交的變更"""
    code, out, err = run("git status --porcelain")
    return out.strip()


def main():
    lock_fd = None
    try:
        # 防止多重執行（如果上次執行還沒完成）
        lock_fd = acquire_lock()
        if lock_fd is None:
            log("上一次執行尚未結束，跳過")
            return
        log("=== Sync start ===")

        os.chdir(REPO_DIR)

        # 確認是 git repo
        code, out, err = run("git rev-parse --git-dir")
        if code != 0:
            log(f"ERROR: 不是 Git repo: {err}")
            return

        # 檢查變更
        changes = check_changes()
        if not changes:
            log("沒有變更，跳過同步")
            log("=== Sync done ===")
            return

        log(f"發現變更:")
        for line in changes.split("\n"):
            if line:
                log(f"  {line}")

        # Stage 所有變更
        code, out, err = run("git add -A")
        if code != 0:
            log(f"git add 失敗: {err}")
            return

        # Commit
        commit_msg = f"sync: {datetime.now().strftime('%Y-%m-%d %H:%M')} local update"
        code, out, err = run(f'git commit -m "{commit_msg}"')
        if code != 0:
            if "nothing to commit" in (out + err).lower():
                log("沒有要提交的變更")
            else:
                log(f"git commit 失敗: {err}")
                return
        else:
            log(f"已 commit: {commit_msg}")

        # Push 到 GitHub
        log("Push to GitHub...")
        code, out, err = run("git push origin main")
        if code != 0:
            # 可能是 remote 有更新的檔案，先 pull 再 push
            log(f"直接 push 失敗: {err.strip()}")
            log("嘗試 pull --rebase...")
            
            code, out, err = run("git pull --rebase origin main")
            if code == 0:
                log("Pull & rebase 成功，重新 push...")
                code, out, err = run("git push origin main")
                if code == 0:
                    log("Push 成功！")
                else:
                    log(f"第二次 push 失敗: {err.strip()}")
            else:
                log(f"Pull 失敗: {err.strip()}")
        else:
            log("Push 成功！")

        log("=== Sync done ===")
    finally:
        # 釋放鎖
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                os.unlink(LOCK_FILE)
            except:
                pass


if __name__ == "__main__":
    main()