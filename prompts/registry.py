"""
PromptRegistry - 統一 Prompt 版本管理、載入、回滾、A/B 測試

功能：
- 載入系統/生成提示詞 (支援版本號、支援 per-mode)
- 版本歷史管理 (儲存至 versions/index.json)
- A/B 測試支援 (並行跑多版本)
- 回滾到最佳版本
- 與 auto_prompt_optimizer 整合
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# 路徑設定
PROMPTS_DIR = Path(__file__).parent
SYSTEM_DIR = PROMPTS_DIR / "system"
GENERATION_DIR = PROMPTS_DIR / "generation"
RULES_DIR = PROMPTS_DIR / "rules"
VERSIONS_DIR = PROMPTS_DIR / "versions"
EVALUATION_DIR = PROMPTS_DIR / "evaluation"

VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = VERSIONS_DIR / "index.json"


class PromptVersion:
    """單一 Prompt 版本資料結構"""

    def __init__(
        self,
        version: int,
        system_prompt: dict[str, str],  # {"tw": "...", "us": "..."}
        generation_prompt: dict[str, str],  # {"tw": "...", "us": "..."}
        rules: str,
        metadata: dict[str, Any] | None = None,
    ):
        self.version = version
        self.system_prompt = system_prompt
        self.generation_prompt = generation_prompt
        self.rules = rules
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.scores: dict[str, float] = {}  # {"tw": 8.5, "us": 8.2, "overall": 8.35}

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "system_prompt": self.system_prompt,
            "generation_prompt": self.generation_prompt,
            "rules": self.rules,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "scores": self.scores,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PromptVersion":
        pv = cls(
            version=data["version"],
            system_prompt=data["system_prompt"],
            generation_prompt=data["generation_prompt"],
            rules=data["rules"],
            metadata=data.get("metadata", {}),
        )
        pv.created_at = data.get("created_at", pv.created_at)
        pv.scores = data.get("scores", {})
        return pv


class PromptRegistry:
    """Prompt 版本註冊表"""

    def __init__(self, auto_load_latest: bool = True):
        self._versions: dict[int, PromptVersion] = {}
        self._current_version: int = 1
        self._best_version: int = 1
        self._ab_test_versions: list[int] = []  # A/B 測試版本列表

        if auto_load_latest:
            self._load_index()

    # ─────────────────────────────────────────────
    # 載入/儲存
    # ─────────────────────────────────────────────

    def _load_index(self) -> None:
        """載入版本索引"""
        if INDEX_FILE.exists():
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._current_version = data.get("current_version", 1)
            self._best_version = data.get("best_version", 1)
            self._ab_test_versions = data.get("ab_test_versions", [])
            for v_data in data.get("versions", []):
                pv = PromptVersion.from_dict(v_data)
                self._versions[pv.version] = pv

    def _save_index(self) -> None:
        """儲存版本索引"""
        data = {
            "current_version": self._current_version,
            "best_version": self._best_version,
            "ab_test_versions": self._ab_test_versions,
            "versions": [v.to_dict() for v in self._versions.values()],
        }
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ─────────────────────────────────────────────
    # 公開 API
    # ─────────────────────────────────────────────

    def get_system_prompt(self, mode: str = "tw", version: int | None = None) -> str:
        """取得系統提示詞 (含共用規則) - 支援 per-mode"""
        v = version or self._current_version
        pv = self._versions.get(v)
        if not pv:
            return self._load_default_system(mode)

        # 取得對應模式的系統提示詞
        sys_prompt = pv.system_prompt.get(mode, pv.system_prompt.get("tw", ""))
        base_rules = self._load_shared_rules()
        return f"{sys_prompt}\n\n---\n\n{base_rules}"

    def get_generation_prompt(self, mode: str = "tw", version: int | None = None) -> str:
        """取得生成提示詞模板"""
        v = version or self._current_version
        pv = self._versions.get(v)
        if not pv:
            return self._load_default_generation(mode)

        template = pv.generation_prompt.get(mode, pv.generation_prompt.get("tw", ""))
        return template

    def get_rules(self) -> str:
        """取得共用規則"""
        return self._load_shared_rules()

    def get_current_version(self) -> int:
        return self._current_version

    def get_best_version(self) -> int:
        return self._best_version

    # ─────────────────────────────────────────────
    # 版本管理
    # ─────────────────────────────────────────────

    def create_version(
        self,
        system_prompt: dict[str, str],
        generation_prompt: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """建立新版本"""
        new_version = max(self._versions.keys(), default=0) + 1
        rules = self._load_shared_rules()
        pv = PromptVersion(new_version, system_prompt, generation_prompt, rules, metadata)
        self._versions[new_version] = pv
        self._current_version = new_version
        self._save_index()
        self._save_version_file(pv)
        return new_version

    def set_current_version(self, version: int) -> bool:
        """切換當前版本"""
        if version in self._versions:
            self._current_version = version
            self._save_index()
            return True
        return False

    def set_best_version(self, version: int) -> bool:
        """設定最佳版本"""
        if version in self._versions:
            self._best_version = version
            self._save_index()
            return True
        return False

    def rollback_to_best(self) -> int:
        """回滾到最佳版本"""
        self._current_version = self._best_version
        self._save_index()
        return self._current_version

    def record_score(self, version: int, mode: str, score: float) -> None:
        """記錄評分"""
        if version in self._versions:
            self._versions[version].scores[mode] = score
            # 更新 overall
            scores = list(self._versions[version].scores.values())
            if scores:
                self._versions[version].scores["overall"] = sum(scores) / len(scores)
            self._save_index()
            self._save_version_file(self._versions[version])

    # ─────────────────────────────────────────────
    # A/B 測試
    # ─────────────────────────────────────────────

    def start_ab_test(self, versions: list[int]) -> None:
        """啟動 A/B 測試 (並行跑多版本)"""
        self._ab_test_versions = [v for v in versions if v in self._versions]
        self._save_index()

    def get_ab_test_versions(self) -> list[int]:
        return self._ab_test_versions.copy()

    def end_ab_test(self, winner_version: int) -> None:
        """結束 A/B 測試，設定獲勝版本為最佳"""
        self.set_best_version(winner_version)
        self._ab_test_versions = []
        self._save_index()

    # ─────────────────────────────────────────────
    # 內部方法
    # ─────────────────────────────────────────────

    def _load_shared_rules(self) -> str:
        rules_file = RULES_DIR / "shared_rules.md"
        if rules_file.exists():
            return rules_file.read_text(encoding="utf-8")
        return ""

    def _load_default_system(self, mode: str) -> str:
        sys_file = SYSTEM_DIR / f"{mode}.md"
        if sys_file.exists():
            return sys_file.read_text(encoding="utf-8")
        base_file = SYSTEM_DIR / "base.md"
        if base_file.exists():
            return base_file.read_text(encoding="utf-8")
        return "你是專業投資播客主持人。"

    def _load_default_generation(self, mode: str) -> str:
        gen_file = GENERATION_DIR / f"{mode}.md"
        if gen_file.exists():
            return gen_file.read_text(encoding="utf-8")
        base_file = GENERATION_DIR / "base.md"
        if base_file.exists():
            return base_file.read_text(encoding="utf-8")
        return "生成 {mode} 版文字稿。"

    def _save_version_file(self, pv: PromptVersion) -> None:
        """單獨儲存版本檔案 (方便人工檢視)"""
        version_file = VERSIONS_DIR / f"v{pv.version}.json"
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(pv.to_dict(), f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# 單例模式 - 全域存取
# ─────────────────────────────────────────────

_registry_instance: PromptRegistry | None = None


def get_registry() -> PromptRegistry:
    """取得全域 PromptRegistry 實例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = PromptRegistry()
    return _registry_instance


def reset_registry() -> None:
    """重置 (測試用)"""
    global _registry_instance
    _registry_instance = None


# ─────────────────────────────────────────────
# 初始化：若無版本，建立 v1
# ─────────────────────────────────────────────

def initialize_default_version() -> None:
    """初始化預設版本 (v1)"""
    registry = get_registry()
    if not registry._versions:
        # 讀取現有檔案建立 v1
        system_tw = (SYSTEM_DIR / "tw.md").read_text(encoding="utf-8") if (SYSTEM_DIR / "tw.md").exists() else ""
        system_us = (SYSTEM_DIR / "us.md").read_text(encoding="utf-8") if (SYSTEM_DIR / "us.md").exists() else ""
        gen_tw = (GENERATION_DIR / "tw.md").read_text(encoding="utf-8") if (GENERATION_DIR / "tw.md").exists() else ""
        gen_us = (GENERATION_DIR / "us.md").read_text(encoding="utf-8") if (GENERATION_DIR / "us.md").exists() else ""
        rules = (RULES_DIR / "shared_rules.md").read_text(encoding="utf-8") if (RULES_DIR / "shared_rules.md").exists() else ""

        registry.create_version(
            system_prompt={"tw": system_tw, "us": system_us},
            generation_prompt={"tw": gen_tw, "us": gen_us},
            metadata={"source": "initial_migration", "description": "從 content_creator.py 遷移"},
        )


if __name__ == "__main__":
    # 測試
    initialize_default_version()
    reg = get_registry()
    print(f"Current version: {reg.get_current_version()}")
    print(f"Best version: {reg.get_best_version()}")
    print(f"Versions: {list(reg._versions.keys())}")
    print(f"System prompt (TW) length: {len(reg.get_system_prompt('tw'))}")
    print(f"System prompt (US) length: {len(reg.get_system_prompt('us'))}")
    print(f"Generation prompt (TW) length: {len(reg.get_generation_prompt('tw'))}")
    print(f"Generation prompt (US) length: {len(reg.get_generation_prompt('us'))}")
