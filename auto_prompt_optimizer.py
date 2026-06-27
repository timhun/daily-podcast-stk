#!/usr/bin/env python3
"""
auto_prompt_optimizer.py - 自動迭代式 Podcast Prompt 優化器

功能：
1. 自動分析每天生成的 podcast 腳本
2. 評估腳本品質（說服力、流暢度、專業性）
3. 根據評估反饋自動優化 prompt
4. 保存 prompt 版本歷史並應用最佳版本
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from nim_api import call_nim

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_optimizer")

# 預設路徑 - 使用相對路徑或環境變數，支援 GitHub Actions
PODCAST_DIR = Path(os.environ.get("PODCAST_DIR", "/home/bbm/podcast"))
PROMPT_DIR = PODCAST_DIR / "prompt_versions"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)
class PromptOptimizer:
    """自動 Prompt 優化器"""
    
    # 預設的 Podcast 系統提示詞
    DEFAULT_SYSTEM_PROMPT = """你是一位專業的投資播客主持人，擅长用簡單生動的語言解讀複雜的金融市場。

風格要求：
- 專業但親和，適合普通投資者聆聽
- 使用台灣用語和口吻
- 數據解讀要具體，不要只播報數字，要說出數字的意義
- 結尾要有明確的投資建議
- 每段敘述要有邏輯銜接，不要跳躍"""

    # 預設的生成提示詞模板
    DEFAULT_GENERATION_PROMPT = """生成 {mode_upper} 投資大師文字稿，長度控制在{length_limit}字內，風格專業親和，使用台灣用語。

文字稿必須是連貫的敘述性文字，適合直接轉換成語音。不要包含任何結構標記如 '-' 或 '*'，不要包含橋段標題或解釋（如 '開場:' 或 '市場概況:'），只需生成完整的、流暢的播客內容。

基於以下內容生成：

開場白：歡迎收聽《幫幫忙說AI投資》，我是幫幫忙。今天是{today}。

市場概況：
{analysis}

產業動態：
{news_str}

市場情緒：
{sentiment_str}

市場分析：
{market_analysis_str}

策略分析：
{strategy_str}

結尾：投資金句（選用 - 科斯托蘭尼 André Kostolany）。

注意事項：
(1) 輸出應為純文字稿，無額外格式。記得你是專業投資大師主播。
(2) 不要播出股票代碼而是直接用股票名稱，如 TWII 為加權指數，2330為台積電。
(3) 不要播報技術指標數字，而是說出數字所代表的意思。不用播報個股報價。
(4) 產業新聞只取半導體及AI相關。
(5) 最後要明確指出 QQQ 和 0050 的買賣策略及大盤多空方向。"""

    def __init__(self):
        self.config_path = PROMPT_DIR / "config.json"
        self.history_path = PROMPT_DIR / "history.json"
        self.scores_path = PROMPT_DIR / "scores.json"
        self.load_config()

    def load_config(self):
        """載入配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "system_prompt": self.DEFAULT_SYSTEM_PROMPT,
                "generation_prompt": self.DEFAULT_GENERATION_PROMPT,
                "length_limit": 2500,
                "target_score": 8.5,
                "current_version": 1,
                "best_version": 1,
                "best_score": 0
            }
            self.save_config()

    def save_config(self):
        """儲存配置"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_latest_scripts(self, limit=5):
        """取得最近生成的腳本"""
        scripts = []
        docs_dir = PODCAST_DIR / "docs"
        if not docs_dir.exists():
            return scripts

        # 找出最近的 podcast 目錄
        for d in sorted(docs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if d.is_dir() and (d.name.endswith('_us') or d.name.endswith('_tw')):
                for txt in d.glob("*.txt"):
                    if "podcast" in txt.name:
                        scripts.append(txt)
                        if len(scripts) >= limit:
                            return scripts
        return scripts

    def evaluate_script(self, script_content: str, mode: str = "us") -> dict:
        """使用 LLM 評估腳本品質"""
        evaluation_prompt = f"""你是一個專業的 Podcast 腳本評審。請評估以下投資播客腳本的品質。

評估維度（每項 1-10 分）：
1. 說服力 - 能否說服聽眾接受觀點
2. 流暢度 - 文字是否自然流暢
3. 專業性 - 投資分析是否準確專業
4. 結構性 - 開場、內容、結尾是否有邏輯
5. 互動性 - 是否有與聽眾互動的感覺

請根據以下腳本給出評分：

{script_content[:3000]}

請用以下 JSON 格式回覆（只需要 JSON，不要其他文字）：
{{
    "persuasion": 8.0,
    "fluency": 8.5,
    "professional": 8.0,
    "structure": 8.5,
    "engagement": 7.5,
    "overall": 8.3,
    "strengths": ["說服力強", "結構清晰"],
    "weaknesses": ["結尾略短"],
    "suggestions": ["可以加強數據解讀"]
}}"""

        try:
            result = call_nim(
                prompt=evaluation_prompt,
                task_type="medium",
                temperature=0.3,
                max_tokens=1500
            )
            
            if result:
                # 嘗試解析 JSON
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    scores = json.loads(json_match.group())
                    return scores
        except Exception as e:
            logger.warning(f"評估腳本失敗: {e}")

        # 備用：簡單評估
        return {
            "persuasion": 7.0,
            "fluency": 7.0,
            "professional": 7.0,
            "structure": 7.0,
            "engagement": 7.0,
            "overall": 7.0,
            "strengths": ["基本合格"],
            "weaknesses": ["未完整評估"],
            "suggestions": ["需要手動檢查"]
        }

    def generate_improved_prompt(self, current_prompt: str, scores: dict, mode: str = "us") -> str:
        """根據評估結果生成改進的 prompt"""
        improvement_prompt = f"""你是 Prompt Engineering 專家。請根據以下評估結果，優化 Podcast 腳本生成 Prompt。

當前 Prompt：
{current_prompt}

評估結果：
- 說服力：{scores.get('persuasion', 7)}
- 流暢度：{scores.get('fluency', 7)}
- 專業性：{scores.get('professional', 7)}
- 結構性：{scores.get('structure', 7)}
- 互動性：{scores.get('engagement', 7)}
- 總分：{scores.get('overall', 7)}

需要改進的方面：{', '.join(scores.get('weaknesses', ['無'])[:3])}
建議：{', '.join(scores.get('suggestions', ['無'])[:3])}

請生成優化後的 Prompt，保留原來的變量佔位符（{{{{analysis}}}}、{{{{today}}}} 等）。

請用以下 JSON 格式回覆：
{{
    "improved_prompt": "優化後的完整 Prompt 文字..."
}}"""

        try:
            result = call_nim(
                prompt=improvement_prompt,
                task_type="medium",
                temperature=0.5,
                max_tokens=2500
            )
            
            if result:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    improved = json.loads(json_match.group())
                    return improved.get('improved_prompt', current_prompt)
        except Exception as e:
            logger.warning(f"生成改進 prompt 失敗: {e}")

        return current_prompt

    def save_version(self, version: int, prompt: str, scores: dict = None):
        """保存 Prompt 版本"""
        version_file = PROMPT_DIR / f"v{version}.json"
        version_data = {
            "version": version,
            "created_at": datetime.now().isoformat(),
            "prompt": prompt,
            "scores": scores
        }
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)
        
        # 更新歷史
        history = []
        if self.history_path.exists():
            with open(self.history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        history.append({
            "version": version,
            "created_at": version_data["created_at"],
            "scores": scores
        })
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def run_daily_optimization(self):
        """執行每日自動優化"""
        logger.info("開始每日 Prompt 自動優化...")
        
        # 1. 取得最新生成的腳本
        scripts = self.get_latest_scripts(limit=3)
        
        if not scripts:
            logger.info("沒有找到最近的腳本，跳過優化")
            return
        
        logger.info(f"找到 {len(scripts)} 個最近生成的腳本")
        
        # 2. 評估最新的腳本
        latest_script = scripts[0]
        with open(latest_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"評估腳本: {latest_script.name}")
        scores = self.evaluate_script(content)
        
        logger.info(f"評估結果: 總分 {scores.get('overall', 0):.1f}/10")
        logger.info(f"  說服力: {scores.get('persuasion', 0):.1f}")
        logger.info(f"  流暢度: {scores.get('fluency', 0):.1f}")
        logger.info(f"  專業性: {scores.get('professional', 0):.1f}")
        
        # 3. 保存當前版本分數
        self.save_version(self.config["current_version"], 
                         self.config["generation_prompt"], 
                         scores)
        
        # 4. 如果分數低於目標，嘗試改進
        target = self.config.get("target_score", 8.5)
        current_overall = scores.get('overall', 0)
        
        if current_overall < target:
            logger.info(f"分數低於目標 ({target})，開始優化...")
            
            new_prompt = self.generate_improved_prompt(
                self.config["generation_prompt"], 
                scores
            )
            
            # 版本++
            new_version = self.config["current_version"] + 1
            self.config["generation_prompt"] = new_prompt
            self.config["current_version"] = new_version
            
            # 如果新版本更好，更新最佳版本
            if current_overall > self.config.get("best_score", 0):
                self.config["best_version"] = new_version
                self.config["best_score"] = current_overall
            
            self.save_config()
            self.save_version(new_version, new_prompt)
            
            logger.info(f"已生成並保存新版本 v{new_version}")
        else:
            logger.info(f"分數已達標 (>{target})，無需優化")
        
        # 5. 保存分數歷史
        scores_history = []
        if self.scores_path.exists():
            with open(self.scores_path, 'r', encoding='utf-8') as f:
                scores_history = json.load(f)
        
        scores_history.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "script": latest_script.name,
            "scores": scores
        })
        
        # 只保留最近 30 天的記錄
        scores_history = scores_history[-30:]
        
        with open(self.scores_path, 'w', encoding='utf-8') as f:
            json.dump(scores_history, f, ensure_ascii=False, indent=2)
        
        logger.info("每日優化完成")
        return scores

    def get_current_prompt(self) -> str:
        """取得當前使用的 Prompt"""
        return self.config["generation_prompt"]

    def get_best_prompt(self) -> str:
        """取得歷史最佳 Prompt"""
        best_version = self.config.get("best_version", 1)
        best_file = PROMPT_DIR / f"v{best_version}.json"
        
        if best_file.exists():
            with open(best_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("prompt", self.DEFAULT_GENERATION_PROMPT)
        
        return self.DEFAULT_GENERATION_PROMPT

def main():
    import argparse
    parser = argparse.ArgumentParser(description="自動 Prompt 優化器")
    parser.add_argument('--status', action='store_true', help='顯示當前狀態')
    parser.add_argument('--reset', action='store_true', help='重置為預設 Prompt')
    args = parser.parse_args()
    
    optimizer = PromptOptimizer()
    
    if args.status:
        print("\n=== Prompt Optimizer 狀態 ===")
        print(f"當前版本: v{optimizer.config['current_version']}")
        print(f"最佳版本: v{optimizer.config['best_version']} (分數: {optimizer.config.get('best_score', 0):.1f})")
        print(f"目標分數: {optimizer.config.get('target_score', 8.5)}")
        print(f"\nPrompt 長度: {len(optimizer.get_current_prompt())} 字")
        print(f"\nPrompt 版本目錄: {PROMPT_DIR}")
        
    elif args.reset:
        optimizer.config["generation_prompt"] = PromptOptimizer.DEFAULT_GENERATION_PROMPT
        optimizer.config["current_version"] = 1
        optimizer.save_config()
        print("已重置為預設 Prompt")
        
    else:
        optimizer.run_daily_optimization()

if __name__ == "__main__":
    main()
