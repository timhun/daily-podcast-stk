#!/usr/bin/env python3
"""
每日自動優化執行腳本
用法：
  python run_daily_optimization.py           # 完整流程：生成→評分→優化
  python run_daily_optimization.py --gen-only  # 僅生成腳本
  python run_daily_optimization.py --eval-only # 僅評分現有腳本
  python run_daily_optimization.py --ab-test   # 執行 A/B 測試
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# 設定路徑
sys.path.insert(0, str(Path(__file__).parent))

from content_creator_v2 import generate_script, evaluate_script_quality, generate_script_with_version
from auto_prompt_optimizer_v2 import PromptOptimizerV2
from prompts.registry import initialize_default_version, get_registry

# ─────────────────────────────────────────────
# 模擬市場數據 (實際部署時替換為真實 collect_data)
# ─────────────────────────────────────────────

def get_mock_market_data(mode: str) -> dict:
    if mode == "tw":
        return {
            "market": {
                "^TWII": {"close": 23000, "change": 1.2},
                "0050.TW": {"close": 150, "change": 1.5},
                "2330.TW": {"close": 980, "change": 2.1},
            },
            "news": [
                {"title": "台積電 3奈米良率突破 80%，下季量產看俏", "description": "台積電最新 3奈米製程良率大幅提升"},
                {"title": "輝達 GB200 訂單暴增，台股 AI 概念股受惠", "description": "NVIDIA 新世代晶片需求強勁"},
                {"title": "OpenAI 發布 GPT-5，推理能力大幅提升", "description": "最新模型在多項基準測試創新高"},
            ],
            "sentiment": {"overall_score": 0.35, "bullish_ratio": 0.7},
        }
    else:
        return {
            "market": {
                "QQQ": {"close": 480, "change": 1.8},
                "SPY": {"close": 560, "change": 1.2},
                "BTC": {"close": 65000, "change": 3.5},
            },
            "news": [
                {"title": "微軟 Azure AI 營收超預期，雲端增長加速", "description": "Microsoft 最新財報顯示 AI 驅動雲端業務"},
                {"title": "Anthropic Claude 3.5 Sonnet 發布，程式設計能力突破", "description": "新模型在 SWE-bench 達到 49% 解決率"},
            ],
            "sentiment": {"overall_score": 0.28, "bullish_ratio": 0.65},
        }

def get_mock_strategy_results(mode: str) -> dict:
    if mode == "tw":
        return {
            "^TWII": {"signals": {"position": "LONG"}},
            "0050.TW": {"signals": {"position": "LONG"}},
            "2330.TW": {"signals": {"position": "LONG"}},
        }
    else:
        return {
            "QQQ": {"signals": {"position": "LONG"}},
            "SPY": {"signals": {"position": "LONG"}},
        }

def get_mock_market_analysis(mode: str) -> dict:
    if mode == "tw":
        return {
            "^TWII": {"trend": "上升", "ta_signal": "BUY"},
            "0050.TW": {"trend": "上升", "ta_signal": "BUY"},
        }
    else:
        return {
            "QQQ": {"trend": "上升", "ta_signal": "BUY"},
            "SPY": {"trend": "上升", "ta_signal": "BUY"},
        }

# ─────────────────────────────────────────────
# 核心流程
# ─────────────────────────────────────────────

def run_generation(mode: str = "tw", version: int = None) -> dict:
    """生成腳本並評分"""
    print(f"\n{'='*60}")
    print(f"📝 生成 {mode.upper()} 版腳本" + (f" (v{version})" if version else " (當前版本)"))
    print(f"{'='*60}")
    
    market_data = get_mock_market_data(mode)
    strategy_results = get_mock_strategy_results(mode)
    market_analysis = get_mock_market_analysis(mode)
    
    if version:
        script, scores = generate_script_with_version(market_data, mode, strategy_results, market_analysis, version)
    else:
        script = generate_script(market_data, mode, strategy_results, market_analysis)
        scores = evaluate_script_quality(script, mode)
    
    print(f"字數: {len(script)}")
    print(f"總分: {scores['overall']}/10")
    print(f"細項: {scores['scores']}")
    if scores.get('violations'):
        print(f"⚠️ 違規: {scores['violations']}")
    
    # 儲存腳本
    today = datetime.now().strftime("%Y%m%d")
    output_dir = Path(f"docs/{today}_{mode}")
    output_dir.mkdir(parents=True, exist_ok=True)
    script_file = output_dir / f"podcast_{today}_{mode}.txt"
    script_file.write_text(script, encoding="utf-8")
    print(f"已儲存: {script_file}")
    
    return {"script": script, "scores": scores, "file": str(script_file)}

def run_evaluation(mode: str = "tw") -> dict:
    """評分現有最新腳本"""
    print(f"\n{'='*60}")
    print(f"📊 評分 {mode.upper()} 版最新腳本")
    print(f"{'='*60}")
    
    # 尋找最新腳本
    docs_dir = Path("docs")
    latest_script = None
    for d in sorted(docs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if d.is_dir() and d.name.endswith(f"_{mode}"):
            for f in d.glob("*.txt"):
                latest_script = f
                break
            if latest_script:
                break
    
    if not latest_script:
        print("❌ 找不到腳本檔案")
        return {}
    
    script = latest_script.read_text(encoding="utf-8")
    scores = evaluate_script_quality(script, mode)
    
    print(f"檔案: {latest_script}")
    print(f"字數: {len(script)}")
    print(f"總分: {scores['overall']}/10")
    print(f"細項: {scores['scores']}")
    if scores.get('violations'):
        print(f"⚠️ 違規: {scores['violations']}")
    
    return {"script": script, "scores": scores, "file": str(latest_script)}

def run_full_optimization() -> dict:
    """完整流程：雙模式生成 → 評分 → 自動優化"""
    print(f"\n{'='*60}")
    print(f"🚀 執行完整每日優化流程")
    print(f"{'='*60}")
    
    # 1. 初始化 Registry
    initialize_default_version()
    
    # 2. 雙模式生成
    results = {}
    for mode in ["tw", "us"]:
        results[mode] = run_generation(mode)
    
    # 3. 自動優化
    optimizer = PromptOptimizerV2()
    scripts = {mode: r["script"] for mode, r in results.items()}
    opt_result = optimizer.run_daily_optimization(scripts)
    
    print(f"\n✅ 優化結果: {json.dumps(opt_result, ensure_ascii=False, indent=2)}")
    
    # 4. 顯示狀態
    status = optimizer.get_status()
    print(f"\n📈 當前狀態:")
    print(f"  當前版本: v{status['current_version']}")
    print(f"  最佳版本: v{status['best_version']}")
    print(f"  待簽核: {len(status['pending_signoffs'])} 筆")
    
    return {"generation": results, "optimization": opt_result, "status": status}

def run_ab_test(v1: int, v2: int, mode: str = "tw") -> dict:
    """執行 A/B 測試"""
    print(f"\n{'='*60}")
    print(f"🧪 A/B 測試: v{v1} vs v{v2} ({mode.upper()})")
    print(f"{'='*60}")
    
    initialize_default_version()
    optimizer = PromptOptimizerV2()
    optimizer.start_ab_test(v1, v2)
    
    market_data = get_mock_market_data(mode)
    strategy_results = get_mock_strategy_results(mode)
    market_analysis = get_mock_market_analysis(mode)
    
    results = {}
    for v in [v1, v2]:
        script, scores = generate_script_with_version(market_data, mode, strategy_results, market_analysis, v)
        eval_result = optimizer.evaluator.evaluate(script, mode, v)
        results[f"v{v}"] = {"script": script, "scores": scores, "eval": eval_result}
        print(f"  v{v}: 總分 {eval_result.overall}/10, 字數 {len(script)}")
    
    # 自動選擇較高分版本
    winner = v1 if results[f"v{v1}"]["eval"].overall >= results[f"v{v2}"]["eval"].overall else v2
    optimizer.end_ab_test(winner)
    print(f"\n🏆 獲勝版本: v{winner}")
    
    return {"results": results, "winner": winner}

# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="每日自動優化執行器")
    parser.add_argument("--mode", choices=["tw", "us", "both"], default="both", help="模式")
    parser.add_argument("--gen-only", action="store_true", help="僅生成腳本")
    parser.add_argument("--eval-only", action="store_true", help="僅評分現有腳本")
    parser.add_argument("--ab-test", nargs=2, type=int, metavar=("V1", "V2"), help="A/B 測試版本號")
    parser.add_argument("--version", type=int, help="指定版本號生成")
    parser.add_argument("--status", action="store_true", help="顯示優化器狀態")
    args = parser.parse_args()
    
    # 確保 Registry 初始化
    initialize_default_version()
    
    if args.status:
        optimizer = PromptOptimizerV2()
        status = optimizer.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return
    
    if args.ab_test:
        run_ab_test(args.ab_test[0], args.ab_test[1], args.mode if args.mode != "both" else "tw")
        return
    
    if args.gen_only:
        if args.mode == "both":
            for m in ["tw", "us"]:
                run_generation(m, args.version)
        else:
            run_generation(args.mode, args.version)
        return
    
    if args.eval_only:
        if args.mode == "both":
            for m in ["tw", "us"]:
                run_evaluation(m)
        else:
            run_evaluation(args.mode)
        return
    
    # 預設：完整流程
    run_full_optimization()

if __name__ == "__main__":
    main()
