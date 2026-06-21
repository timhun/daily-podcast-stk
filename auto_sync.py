#!/usr/bin/env python3
"""
auto_sync.py - 自動同步本地變更到 GitHub
自動 commit 並 push 到 GitHub（只有檔案有實際變更才會 commit）
"""

import subprocess
import sys
import os
from datetime import datetime

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd, cwd=REPO_DIR, capture=True):
    """執行 shell 命令"""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def get_status():
    """檢查 git status"""
    code, out, err = run("git status --porcelain", capture=True)
    return out.strip()


def get_diff_files():
    """取得已變更的檔案列表"""
    code, out, err = run("git diff --name-only", capture=True)
    return [f for f in out.strip().split("\n") if f]


def main():
    os.chdir(REPO_DIR)
    
    # 檢查是否有變更
    status = get_status()
    if not status:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 沒有變更，跳過同步")
        return

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 發現變更:")
    
    changed_files = status.split("\n")
    for f in changed_files:
        if f:
            print(f"  {f}")

    # 取得變更檔案列表用於 commit message
    diff_files = get_diff_files()
    files_summary = ", ".join(diff_files[:5])
    if len(diff_files) > 5:
        files_summary += f" (+{len(diff_files) - 5} more)"

    # Commit
    commit_msg = f"sync: {datetime.now().strftime('%Y-%m-%d %H:%M')} local update"
    
    print(f"\n執行 git add ...")
    code, out, err = run("git add -A")
    if code != 0:
        print(f"  git add 失敗: {err}")
        return

    print(f"執行 git commit: {commit_msg}")
    code, out, err = run(f'git commit -m "{commit_msg}"')
    if code != 0:
        # 可能已經是最新的（例如另一個進程剛剛 commit 了）
        if "nothing to commit" in out or "nothing to commit" in err:
            print("  沒有要提交的變更（可能已被其他進程處理）")
            return
        print(f"  git commit 失敗: {err}")
        return

    # Push
    print(f"執行 git push origin main...")
    code, out, err = run("git push origin main")
    if code != 0:
        print(f"  git push 失敗: {err}")
        # 嘗試 pull 再 push
        print("  嘗試 pull 並重新 push...")
        code, out, err = run("git pull --rebase origin main")
        if code == 0:
            code, out, err = run("git push origin main")
            if code == 0:
                print("  pull & push 成功！")
            else:
                print(f"  第二次 push 失敗: {err}")
                sys.exit(1)
        else:
            print(f"  pull 失敗: {err}")
            sys.exit(1)
    else:
        print(f"  同步成功！")


if __name__ == "__main__":
    main()