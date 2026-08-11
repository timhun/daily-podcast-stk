"""
完整流程測試：
1. 模擬市場數據
2. 雙模式生成腳本 (TW + US)
3. LLM 評審
4. 自動優化 (若分數 < 8.5)
5. A/B 測試演示
"""

from content_creator_v2 import generate_script, evaluate_script_quality
from auto_prompt_optimizer_v2 import PromptOptimizerV2, LLMEvaluator
from prompts.registry import get_registry

# 模擬市場數據
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

def main():
    print("=" * 60)
    print("完整流程測試：雙模式生成 + 評分 + 優化")
    print("=" * 60)
    
    registry = get_registry()
    optimizer = PromptOptimizerV2()
    
    # 1. 雙模式生成
    print("\n📝 步驟 1: 生成 TW / US 腳本")
    scripts = {}
    for mode in ["tw", "us"]:
        print(f"\n--- 生成 {mode.upper()} 版 ---")
        market_data = get_mock_market_data(mode)
        strategy_results = get_mock_strategy_results(mode)
        market_analysis = get_mock_market_analysis(mode)
        
        script = generate_script(market_data, mode, strategy_results, market_analysis)
        scripts[mode] = script
        
        print(f"字數: {len(script)}")
        print(f"前 200 字:\n{script[:200]}...")
    
    # 2. 評分
    print("\n📊 步驟 2: LLM 評審")
    eval_results = {}
    for mode, script in scripts.items():
        print(f"\n--- 評審 {mode.upper()} 版 ---")
        eval_result = optimizer.evaluator.evaluate(script, mode, registry.get_current_version())
        eval_results[mode] = eval_result
        print(f"總分: {eval_result.overall}/10 (by {eval_result.evaluated_by})")
        print(f"細項: {eval_result.scores}")
        if eval_result.violations:
            print(f"⚠️ 違規: {eval_result.violations}")
    
    # 3. 自動優化
    print("\n🔧 步驟 3: 自動優化 (若分數 < 8.5)")
    opt_result = optimizer.run_daily_optimization(scripts)
    print(f"\n優化結果: {opt_result}")
    
    # 4. 顯示狀態
    print("\n📈 步驟 4: 當前狀態")
    status = optimizer.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    # 5. A/B 測試演示
    print("\n🧪 步驟 5: A/B 測試演示 (建立 v2 並對比)")
    # 手動建立一個 v2 作為對比
    from prompts.registry import PromptVersion
    current_pv = registry._versions.get(1)
    if current_pv:
        registry.create_version(
            system_prompt=current_pv.system_prompt,
            generation_prompt=current_pv.generation_prompt,
            metadata={"source": "manual_v2", "description": "測試用 v2"},
        )
    
    optimizer.start_ab_test(1, 2)
    print(f"A/B 測試版本: {optimizer.registry.get_ab_test_versions()}")
    
    # 模擬 A/B 生成 (只跑 TW)
    for v in [1, 2]:
        script = generate_script(
            get_mock_market_data("tw"),
            "tw",
            get_mock_strategy_results("tw"),
            get_mock_market_analysis("tw"),
            version=v
        )
        eval_result = optimizer.evaluator.evaluate(script, "tw", v)
        print(f"  v{v}: 分數 {eval_result.overall}, 字數 {len(script)}")
    
    optimizer.end_ab_test(2)
    print(f"A/B 測試結束，獲勝版本設為最佳: v{optimizer.registry.get_best_version()}")
    
    print("\n" + "=" * 60)
    print("✅ 完整流程測試完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
