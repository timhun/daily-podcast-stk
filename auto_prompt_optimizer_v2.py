"""
auto_prompt_optimizer_v2.py - 升級版：雙軌優化 + LLM 評審 + A/B 測試 + 人工簽核

新功能：
1. 雙軌優化：獨立優化 system_prompt 和 generation_prompt
2. LLM 評審：用大模型而非啟發式評分
3. A/B 測試：並行跑多版本，自動選優
4. 人工簽核關卡：關鍵版本需人工確認
5. 評估指標體系：說服力/流暢度/專業性/結構/合規/長度
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict

# 內部模組
from prompts.registry import get_registry, PromptRegistry, PromptVersion
from content_creator_v2 import evaluate_script_quality
from nim_api import call_nim

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_optimizer_v2")

# 路徑設定
PODCAST_DIR = Path(os.environ.get("PODCAST_DIR", "/home/bbm/podcast"))
PROMPTS_DIR = Path(__file__).parent / "prompts"
VERSIONS_DIR = PROMPTS_DIR / "versions"
EVALUATION_DIR = PROMPTS_DIR / "evaluation"
HUMAN_SIGNOFF_DIR = PROMPTS_DIR / "human_signoff"

VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
HUMAN_SIGNOFF_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 評估標準定義
# ─────────────────────────────────────────────

EVALUATION_CRITERIA = """
# Podcast 腳本評估標準 (供 LLM 評審使用)

## 評分維度 (每項 1-10 分)

### 1. 說服力
- 10: 觀點鮮明有力，論據充分，能強烈說服聽眾採取行動
- 7-9: 觀點清晰，有邏輯支撐，有一定說服力
- 4-6: 觀點模糊，論據薄弱，說服力一般
- 1-3: 無明確觀點，純資訊堆砌，無說服力

### 2. 流暢度
- 10: 文字如行雲流水，口語化極強，極適合 TTS
- 7-9: 語句通順，少許書面語，整體流暢
- 4-6: 有明顯生硬處，部分長句難唸
- 1-3: 斷裂、重複、語病多，不適合語音

### 3. 專業性
- 10: 分析深度專業，術語用法精準，見解獨到
- 7-9: 有一定專業度，術語大致正確
- 4-6: 淺顯，甚至有錯誤認知
- 1-3: 外行話，專業術語濫用或錯誤

### 4. 結構性
- 10: 開場鉤子強、主體層層遞進、金句收尾完美
- 7-9: 有明確開中結，邏輯清晰
- 4-6: 結構鬆散，段落跳躍
- 1-3: 無結構，資訊堆砌

### 5. 合規性 (硬性門檻)
- 10: 完全符合所有硬性規則
- 8-9: 僅有極輕微違規 (如單一代碼殘留)
- 5-7: 多項違規但核心內容完整
- 1-4: 嚴重違規 (大量代碼、CSV、無立場、無金句)

### 6. 長度適配度
- 10: 2500-3500 字 (7-10 分鐘節目)
- 7-9: 2000-2500 或 3500-4000 字
- 4-6: 1500-2000 或 4000-5000 字
- 1-3: <1500 或 >5000 字

## 總分計算
- 加權平均：說服力 25% + 流暢度 20% + 專業性 25% + 結構性 15% + 合規性 10% + 長度 5%
- 門檻：合規性 < 6 分直接判定不合格，無論總分多高
"""


@dataclass
class EvaluationResult:
    """評估結果"""
    overall: float
    scores: dict[str, float]  # 各維度分數
    violations: list[str]
    char_count: int
    mode: str
    version: int
    evaluated_by: str  # "llm" 或 "heuristic"
    raw_response: str | None = None


# ─────────────────────────────────────────────
# LLM 評審器
# ─────────────────────────────────────────────

class LLMEvaluator:
    """使用 LLM 進行專業評審"""

    def __init__(self, model: str = None):
        self.model = model

    def evaluate(self, script: str, mode: str, version: int) -> EvaluationResult:
        """LLM 完整評審"""
        
        eval_prompt = f"""你是專業的投資 Podcast 腳本評審。請只輸出有效 JSON，不要任何解釋文字。

## 待評腳本 (模式: {mode.upper()}, 版本: v{version})
{script}

## 評分標準 (1-10分):
- persuasion (說服力): 觀點鮮明、論據充分、能說服聽眾
- fluency (流暢度): 文字如行雲流水、口語化強、適合TTS
- professional (專業性): 分析深度專業、術語用法精準
- structure (結構性): 開場鉤子強、主體層層遞進、金句收尾完美
- compliance (合規性): 完全符合硬性規則(無代碼、無CSV、無指標數值、有立場、有金句、≥2500字)
- length (長度適配度): 2500-3500字最佳

## 請輸出 JSON (僅 JSON，無markdown、無代碼塊、無說明):
{{
  "persuasion": 8.5,
  "fluency": 9.0,
  "professional": 8.0,
  "structure": 8.5,
  "compliance": 10.0,
  "length": 9.0,
  "violations": [],
  "reasoning": "簡要說明"
}}"""

        try:
            response = call_nim(
                prompt=eval_prompt,
                task_type="json",
                model=self.model,
                system="你是嚴格的 Podcast 腳本評審，只輸出 JSON。",
                max_tokens=1024,
            )
            
            if response:
                result = json.loads(response)
                scores = {k: float(result[k]) for k in ["persuasion", "fluency", "professional", "structure", "compliance", "length"]}
                
                # 加權計算總分
                weights = {"persuasion": 0.25, "fluency": 0.20, "professional": 0.25, 
                          "structure": 0.15, "compliance": 0.10, "length": 0.05}
                overall = sum(scores[k] * weights[k] for k in scores)
                
                # 合規性門檻
                if scores["compliance"] < 6:
                    overall = min(overall, 5.0)
                
                return EvaluationResult(
                    overall=round(overall, 1),
                    scores=scores,
                    violations=result.get("violations", []),
                    char_count=len(script),
                    mode=mode,
                    version=version,
                    evaluated_by="llm",
                    raw_response=response,
                )
        except Exception as e:
            logger.warning(f"LLM 評審失敗，降級啟發式: {e}")
        
        # 降級啟發式
        return self._heuristic_fallback(script, mode, version)

    def _heuristic_fallback(self, script: str, mode: str, version: int) -> EvaluationResult:
        """啟發式評分降級"""
        from content_creator_v2 import evaluate_script_quality
        result = evaluate_script_quality(script, mode)
        return EvaluationResult(
            overall=result["overall"],
            scores=result["scores"],
            violations=result["violations"],
            char_count=result["char_count"],
            mode=mode,
            version=version,
            evaluated_by="heuristic",
        )


# ─────────────────────────────────────────────
# 優化器核心
# ─────────────────────────────────────────────

class PromptOptimizerV2:
    """雙軌 Prompt 自動優化器"""

    def __init__(self):
        self.registry = get_registry()
        self.evaluator = LLMEvaluator()
        
        # 歷史記錄
        self.history_file = VERSIONS_DIR / "optimization_history.json"
        self.signoff_file = HUMAN_SIGNOFF_DIR / "pending_signoff.json"
        
        self._load_history()

    def _load_history(self) -> None:
        self.history = []
        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)

    def _save_history(self) -> None:
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    # ─────────────────────────────────────────────
    # 核心優化流程
    # ─────────────────────────────────────────────

    def run_daily_optimization(self, scripts: dict[str, str] | None = None) -> dict:
        """
        每日自動優化主流程
        
        參數:
            scripts: {{"tw": "腳本內容", "us": "腳本內容"}} 若為 None 則自動讀取最新
        
        返回:
            優化結果摘要
        """
        logger.info("=== 開始每日 Prompt 雙軌優化 ===")
        
        # 1. 取得最新腳本
        if scripts is None:
            scripts = self._get_latest_scripts()
        
        if not scripts:
            logger.info("無可用腳本，跳過優化")
            return {"status": "skipped", "reason": "no scripts"}
        
        results = {}
        
        # 2. 對每個模式分別評估並優化
        for mode, script in scripts.items():
            logger.info(f"處理 {mode.upper()} 模式...")
            
            current_version = self.registry.get_current_version()
            
            # 評估
            eval_result = self.evaluator.evaluate(script, mode, current_version)
            logger.info(f"  評分: {eval_result.overall}/10 (by {eval_result.evaluated_by})")
            logger.info(f"  細項: {eval_result.scores}")
            if eval_result.violations:
                logger.warning(f"  違規: {eval_result.violations}")
            
            # 記錄評分到 Registry
            self.registry.record_score(current_version, mode, eval_result.overall)
            
            # 記錄歷史
            self._record_evaluation(mode, current_version, eval_result)
            
            # 判斷是否需要優化
            target_score = 8.5
            need_optimize = eval_result.overall < target_score
            
            if need_optimize:
                logger.info(f"  分數 {eval_result.overall} < 目標 {target_score}，啟動雙軌優化...")
                
                # 雙軌優化：分別優化 system 和 generation
                new_system = self._optimize_system_prompt(mode, script, eval_result)
                new_generation = self._optimize_generation_prompt(mode, script, eval_result)
                
                # 建立新版本
                new_version = self._create_optimized_version(mode, new_system, new_generation, eval_result)
                
                results[mode] = {
                    "old_version": current_version,
                    "new_version": new_version,
                    "old_score": eval_result.overall,
                    "optimized": True,
                }
                
                # 檢查是否需人工簽核
                if self._needs_human_signoff(eval_result):
                    self._request_human_signoff(mode, new_version, eval_result)
                    results[mode]["needs_signoff"] = True
            else:
                logger.info(f"  分數達標，無需優化")
                results[mode] = {
                    "version": current_version,
                    "score": eval_result.overall,
                    "optimized": False,
                }
        
        logger.info("=== 每日優化完成 ===")
        return {"status": "completed", "results": results}

    # ─────────────────────────────────────────────
    # 雙軌優化：系統提示詞
    # ─────────────────────────────────────────────

    def _optimize_system_prompt(self, mode: str, script: str, eval_result: EvaluationResult) -> str:
        """優化系統提示詞 (身份、風格、核心原則)"""
        
        current_system = self.registry.get_system_prompt(mode)
        
        prompt = f"""你是 Prompt 工程專家。請優化以下系統提示詞，解決腳本評分中的弱點。

## 當前系統提示詞 ({mode.upper()}):
{current_system}

## 腳本評分弱點分析:
- 總分: {eval_result.overall}/10
- 細項: {json.dumps(eval_result.scores, ensure_ascii=False)}
- 違規項目: {eval_result.violations}

## 腳本範例 (前 1000 字):
{script[:1000]}

## 優化目標:
1. 強化說服力：更明確的立場要求、更強的論證結構
2. 提升流暢度：更自然的口語化引導、避免生硬過渡
3. 確保專業性：精準的術語使用規範、深度分析框架
4. 改善結構性：更清晰的段落劃分、鉤子/主體/金句模板
5. 硬性合規：將所有禁止事項內化為正面指令

## 輸出要求:
- 僅輸出優化後的系統提示詞完整內容
- 保持 Markdown 格式
- 不要輸出任何解釋或 JSON
- 針對 {mode.upper()} 模式特性優化 (TW: 台股/0050/台積電; US: QQQ/SPY/BTC/公債)"""

        response = call_nim(
            prompt=prompt,
            task_type="deep",
            
            system="你是頂級 Prompt 工程師，專精投資播客提示詞優化。只輸出優化後的提示詞。",
            max_tokens=4096,
        )
        
        return response if response else current_system

    # ─────────────────────────────────────────────
    # 雙軌優化：生成提示詞
    # ─────────────────────────────────────────────

    def _optimize_generation_prompt(self, mode: str, script: str, eval_result: EvaluationResult) -> str:
        """優化生成提示詞 (模板、變數、格式)"""
        
        current_generation = self.registry.get_generation_prompt(mode)
        
        prompt = f"""你是 Prompt 工程專家。請優化以下生成提示詞模板，解決腳本評分中的弱點。

## 當前生成提示詞 ({mode.upper()}):
{current_generation}

## 腳本評分弱點分析:
- 總分: {eval_result.overall}/10
- 細項: {json.dumps(eval_result.scores, ensure_ascii=False)}
- 違規項目: {eval_result.violations}

## 腳本範例 (前 1000 字):
{script[:1000]}

## 優化目標:
1. 變數命名更清晰，模板結構更合理
2. 明確的字數分配指引 (開場/主體/結尾)
3. 具體的寫作技巧範例 (如何寫鉤子、如何連結新聞與投資、如何寫金句)
4. 針對弱項的針對性指令 (如長度不足→明確要求擴展技巧)
5. 輸出格式約束更精確

## 輸出要求:
- 僅輸出優化後的生成提示詞模板完整內容
- 保持 Markdown 格式，變數用 {{variable}} 格式
- 不要輸出任何解釋或 JSON
- 針對 {mode.upper()} 模式特性優化"""

        response = call_nim(
            prompt=prompt,
            task_type="deep",
            
            system="你是頂級 Prompt 工程師，專精投資播客提示詞優化。只輸出優化後的提示詞。",
            max_tokens=4096,
        )
        
        return response if response else current_generation

    # ─────────────────────────────────────────────
    # 建立新版本
    # ─────────────────────────────────────────────

    def _create_optimized_version(self, mode: str, new_system: str, new_generation: str, eval_result: EvaluationResult) -> int:
        """建立優化後的新版本"""
        
        # 取得另一模式的現有提示詞 (保持不變)
        other_mode = "us" if mode == "tw" else "tw"
        current_version = self.registry.get_current_version()
        current_pv = self.registry._versions.get(current_version)
        
        if current_pv:
            system_prompts = {
                mode: new_system,
                other_mode: current_pv.system_prompt.get(other_mode, "")
            }
            generation_prompts = {
                mode: new_generation,
                other_mode: current_pv.generation_prompt.get(other_mode, "")
            }
        else:
            system_prompts = {mode: new_system, other_mode: ""}
            generation_prompts = {mode: new_generation, other_mode: ""}
        
        new_version = self.registry.create_version(
            system_prompt=system_prompts,
            generation_prompt=generation_prompts,
            metadata={
                "source": "auto_optimization",
                "trigger_mode": mode,
                "trigger_score": eval_result.overall,
                "trigger_violations": eval_result.violations,
                "optimized_tracks": ["system", "generation"],
            }
        )
        
        logger.info(f"已建立新版本 v{new_version} (優化 {mode.upper()} 雙軌)")
        return new_version

    # ─────────────────────────────────────────────
    # 人工簽核關卡
    # ─────────────────────────────────────────────

    def _needs_human_signoff(self, eval_result: EvaluationResult) -> bool:
        """判斷是否需要人工簽核"""
        # 合規性嚴重不足
        if eval_result.scores.get("compliance", 10) < 6:
            return True
        # 專業性極低
        if eval_result.scores.get("professional", 10) < 5:
            return True
        # 版本號是 5 的倍數 (里程碑)
        if self.registry.get_current_version() % 5 == 0:
            return True
        return False

    def _request_human_signoff(self, mode: str, version: int, eval_result: EvaluationResult) -> None:
        """建立人工簽核請求"""
        request = {
            "id": f"signoff_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "mode": mode,
            "version": version,
            "score": eval_result.overall,
            "violations": eval_result.violations,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "reason": "合規性/專業性不足或里程碑版本",
        }
        
        pending = []
        if self.signoff_file.exists():
            with open(self.signoff_file, "r", encoding="utf-8") as f:
                pending = json.load(f)
        
        pending.append(request)
        with open(self.signoff_file, "w", encoding="utf-8") as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)
        
        logger.warning(f"⚠️ 需人工簽核: {self.signoff_file}")

    def approve_version(self, signoff_id: str, approved: bool, notes: str = "") -> bool:
        """人工簽核決定"""
        if not self.signoff_file.exists():
            return False
        
        with open(self.signoff_file, "r", encoding="utf-8") as f:
            pending = json.load(f)
        
        for req in pending:
            if req["id"] == signoff_id:
                req["status"] = "approved" if approved else "rejected"
                req["notes"] = notes
                req["decided_at"] = datetime.now().isoformat()
                
                if approved:
                    # 設為最佳版本
                    self.registry.set_best_version(req["version"])
                    logger.info(f"✅ 版本 v{req['version']} 已核准並設為最佳")
                else:
                    # 回滾
                    self.registry.rollback_to_best()
                    logger.info(f"❌ 版本 v{req['version']} 被拒絕，已回滾")
                
                with open(self.signoff_file, "w", encoding="utf-8") as f:
                    json.dump(pending, f, ensure_ascii=False, indent=2)
                return True
        return False

    # ─────────────────────────────────────────────
    # A/B 測試支援
    # ─────────────────────────────────────────────

    def start_ab_test(self, version_a: int, version_b: int) -> None:
        """啟動 A/B 測試"""
        self.registry.start_ab_test([version_a, version_b])
        logger.info(f"啟動 A/B 測試: v{version_a} vs v{version_b}")

    def run_ab_test_generation(self, market_data: dict, mode: str, 
                                strategy_results: dict, market_analysis: dict) -> dict:
        """並行生成 A/B 版本腳本"""
        versions = self.registry.get_ab_test_versions()
        if len(versions) != 2:
            return {"error": "A/B 測試需恰好 2 個版本"}
        
        results = {}
        for v in versions:
            from content_creator_v2 import generate_script_with_version
            script, scores = generate_script_with_version(market_data, mode, strategy_results, market_analysis, v)
            eval_result = self.evaluator.evaluate(script, mode, v)
            results[f"v{v}"] = {
                "script": script,
                "scores": scores,
                "eval": eval_result,
            }
        
        return results

    def end_ab_test(self, winner_version: int) -> None:
        """結束 A/B 測試"""
        self.registry.end_ab_test(winner_version)
        logger.info(f"A/B 測試結束，獲勝版本: v{winner_version}")

    # ─────────────────────────────────────────────
    # 輔助方法
    # ─────────────────────────────────────────────

    def _get_latest_scripts(self) -> dict[str, str]:
        """讀取最新生成的腳本"""
        scripts = {}
        docs_dir = PODCAST_DIR / "docs"
        if not docs_dir.exists():
            return scripts
        
        for mode in ["tw", "us"]:
            for d in sorted(docs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if d.is_dir() and d.name.endswith(f"_{mode}"):
                    for txt in d.glob("*.txt"):
                        if "podcast" in txt.name.lower():
                            scripts[mode] = txt.read_text(encoding="utf-8")
                            break
                    if mode in scripts:
                        break
        return scripts

    def _record_evaluation(self, mode: str, version: int, eval_result: EvaluationResult) -> None:
        """記錄評估歷史"""
        self.history.append({
            "date": datetime.now().isoformat(),
            "mode": mode,
            "version": version,
            "overall": eval_result.overall,
            "scores": eval_result.scores,
            "violations": eval_result.violations,
            "char_count": eval_result.char_count,
            "evaluated_by": eval_result.evaluated_by,
        })
        # 保留最近 100 筆
        self.history = self.history[-100:]
        self._save_history()

    def get_status(self) -> dict:
        """取得優化器狀態"""
        return {
            "current_version": self.registry.get_current_version(),
            "best_version": self.registry.get_best_version(),
            "ab_test_versions": self.registry.get_ab_test_versions(),
            "pending_signoffs": self._get_pending_signoffs(),
            "recent_history": self.history[-5:] if self.history else [],
        }

    def _get_pending_signoffs(self) -> list:
        if self.signoff_file.exists():
            with open(self.signoff_file, "r", encoding="utf-8") as f:
                return [s for s in json.load(f) if s["status"] == "pending"]
        return []


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prompt 雙軌自動優化器 v2")
    parser.add_argument("--run", action="store_true", help="執行每日優化")
    parser.add_argument("--status", action="store_true", help="顯示狀態")
    parser.add_argument("--ab-test", nargs=2, type=int, metavar=("V1", "V2"), help="啟動 A/B 測試")
    parser.add_argument("--ab-end", type=int, help="結束 A/B 測試，指定獲勝版本")
    parser.add_argument("--signoff", nargs=2, metavar=("ID", "APPROVE"), help="人工簽核 (ID approve/reject)")
    parser.add_argument("--rollback", action="store_true", help="回滾到最佳版本")
    args = parser.parse_args()

    optimizer = PromptOptimizerV2()

    if args.status:
        status = optimizer.get_status()
        print("\n=== Prompt Optimizer V2 狀態 ===")
        print(f"當前版本: v{status['current_version']}")
        print(f"最佳版本: v{status['best_version']}")
        print(f"A/B 測試版本: {status['ab_test_versions']}")
        print(f"待簽核: {len(status['pending_signoffs'])} 筆")
        for s in status['pending_signoffs']:
            print(f"  - {s['id']}: v{s['version']} ({s['mode']}) 分數 {s['score']}")
        print(f"近期歷史: {len(status['recent_history'])} 筆")

    elif args.run:
        result = optimizer.run_daily_optimization()
        print(f"\n優化結果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    elif args.ab_test:
        optimizer.start_ab_test(args.ab_test[0], args.ab_test[1])
        print(f"已啟動 A/B 測試: v{args.ab_test[0]} vs v{args.ab_test[1]}")

    elif args.ab_end:
        optimizer.end_ab_test(args.ab_end)
        print(f"已結束 A/B 測試，獲勝版本: v{args.ab_end}")

    elif args.signoff:
        signoff_id, decision = args.signoff
        approved = decision.lower() in ["approve", "yes", "true", "1"]
        if optimizer.approve_version(signoff_id, approved):
            print(f"簽核完成: {signoff_id} -> {'核准' if approved else '拒絕'}")
        else:
            print(f"簽核失敗: 找不到 {signoff_id}")

    elif args.rollback:
        v = optimizer.registry.rollback_to_best()
        print(f"已回滾到最佳版本: v{v}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
