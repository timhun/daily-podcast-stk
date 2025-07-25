import os

# 根目錄
root = "docs/podcast"

# 遍歷所有子資料夾
for folder in sorted(os.listdir(root), reverse=True):
    full_path = os.path.join(root, folder)
    script_path = os.path.join(full_path, "script.txt")
    summary_path = os.path.join(full_path, "summary.txt")

    if not os.path.isdir(full_path):
        continue
    if not os.path.exists(script_path):
        print(f"⚠️ 跳過：找不到 script.txt - {folder}")
        continue
    if os.path.exists(summary_path):
        print(f"✅ 已存在 summary.txt - {folder}")
        continue

    with open(script_path, "r", encoding="utf-8") as f:
        script = f.read().strip()

    summary = script[:200].replace("\n", " ").strip()
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"✅ 產生 summary.txt - {folder}")
