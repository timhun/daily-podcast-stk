"""
Prompts Package - 模組化 Prompt 管理系統

結構：
prompts/
├── __init__.py           # 公開介面
├── registry.py           # PromptRegistry 核心類別
├── system/               # 系統提示詞 (身份、原則、風格)
│   ├── tw.md
│   ├── us.md
│   └── base.md
├── generation/           # 生成提示詞 (模板、變數、格式)
│   ├── tw.md
│   ├── us.md
│   └── base.md
├── rules/                # 共用規則 (硬性約束)
│   └── shared_rules.md
├── versions/             # 版本歷史 (JSON)
│   ├── v1.json, v2.json...
│   └── index.json
└── evaluation/           # 評估指標與評分標準
    └── criteria.md
"""

from .registry import PromptRegistry, PromptVersion

__all__ = ["PromptRegistry", "PromptVersion"]
