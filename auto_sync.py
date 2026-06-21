#!/usr/bin/env python3
"""
auto_sync.py - 雙向自動同步 daily-podcast-stk 與 GitHub
功能：
- 每 5 分鐘檢查一次
- 本地有變更 → 自動 commit & push 到 GitHub
- GitHub 有變更 → 自動 pull 到本地
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
TOKEN_FILE = os.path.expanduser("~/.netrc")


def log(msg):
    """寫入 log"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
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


def check_local_changes():
    """檢查本地是否有未提交的變更"""
    code, out, err = run("git status --porcelain")
    return out.strip()


def check_remote_updates():
    """檢查 GitHub 是否有更新的內容（fetch 並比較）"""
    # 先 fetch 獲取 remote 最新資訊
    code, out, err = run("git fetch origin main")
    if code != 0:
        return False, "fetch failed"
    
    # 比較本地 HEAD 和 remote HEAD
    code, local, err = run("git rev-parse HEAD")
    code, remote, err = run("git rev-parse origin/main")
    
    if local.strip() != remote.strip():
        return True, f"local={local.strip()[:8]} remote={remote.strip()[:8]}"
    return False, ""


def auto_commit_push():
    """本地有變更 → commit & push"""
    changes = check_local_changes()
    if not changes:
        return False, "no local changes"
    
    log(f"發現本地變更:")
    for line in changes.split("\n"):
        if line:
            log(f"  {line}")
    
    # Stage 所有變更
    code, out, err = run("git add -A")
    if code != 0:
        log(f"git add 失敗: {err}")
        return False, "git add failed"
    
    # Commit
    commit_msg = f"sync: {datetime.now().strftime('%Y-%m-%d %H:%M')} local update"
    code, out, err = run(f'git commit -m "{commit_msg}"')
    if code != 0:
        if "nothing to commit" in (out + err).lower():
            return False, "nothing to commit"
        else:
            log(f"git commit 失敗: {err}")
            return False, "commit failed"
    else:
        log(f"已 commit: {commit_msg}")
    
    # Push 到 GitHub
    log("Push to GitHub...")
    code, out, err = run("git push origin main")
    if code != 0:
        log(f"Push 失敗: {err.strip()}")
        # 嘗試 pull --rebase
        log("嘗試 pull --rebase...")
        code, out, err = run("git pull --rebase origin main")
        if code == 0:
            log("Pull & rebase 成功，重新 push...")
            code, out, err = run("git push origin main")
            if code == 0:
                log("Push 成功！")
                return True, "push success after rebase"
            else:
                return False, "push failed after rebase"
        else:
            return False, "pull failed"
    else:
        log("Push 成功！")
        return True, "push success"
    
    return True, "done"


def auto_pull():
    """GitHub 有更新 → pull 到本地"""
    has_update, info = check_remote_updates()
    if not has_update:
        return False, "no remote updates"
    
    log(f"發現 GitHub 有更新: {info}")
    log("執行 git pull...")
    
    code, out, err = run("git pull origin main")
    if code == 0:
        log(f"Pull 成功！")
        # 顯示更新的內容
        code, out, err = run("git log --oneline -5")
        log(f"最近 commits:\n{out}")
        return True, "pull success"
    else:
        log(f"Pull 失敗: {err.strip()}")
        return False, "pull failed"


def main():
    lock_fd = None
    try:
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
        
        # Step 1: 先 pull GitHub 的更新（雙向同步）
        pulled, pull_msg = auto_pull()
        if pulled:
            log(f"Remote pull: {pull_msg}")
        
        # Step 2: 再 push 本地更新
        pushed, push_msg = auto_commit_push()
        if pushed:
            log(f"Local push: {push_msg}")
        
        if not pulled and not pushed:
            log("沒有變更需要同步")
        
        log("=== Sync done ===")
        
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                os.unlink(LOCK_FILE)
            except:
                pass


if __name__ == "__main__":
    main()
