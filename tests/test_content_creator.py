import content_creator as cc


def _strategy_result(expected, position):
    return {
        "expected_return": expected,
        "max_drawdown": 0.1,
        "sharpe_ratio": 1.2,
        "signals": {"position": position},
    }


def test_generate_script_prompt_captures_dual_strategy_summary(monkeypatch):
    captured = {}

    def fake_generate_script_with_llm(prompt):
        captured["prompt"] = prompt
        return "LLM output"

    monkeypatch.setattr(cc, "generate_script_with_llm", fake_generate_script_with_llm)

    strategy_results = {
        "SPY": {
            "strategy": "god_system",
            "expected_return": 12.345,
            "signals": {"position": "LONG"},
            "strategies": {
                "god_system": _strategy_result(12.345, "LONG"),
                "bigline": _strategy_result(9.876, "SHORT"),
            },
        }
    }

    market_data = {
        "market": {"SPY": {"close": 500, "change": 1.25}},
        "news": [],
        "sentiment": {"overall_score": 0.4, "bullish_ratio": 0.6},
    }

    result = cc.generate_script(market_data, "us", strategy_results, {"SPY": {"trend": "UP", "volatility": 2.5, "report": "Solid momentum"}})
    assert result == "LLM output"

    prompt = captured["prompt"]
    assert "策略分析" in prompt
    assert "SPY: 最佳策略 god_system，預期回報 12.35%，訊號 LONG。" in prompt
    assert "god_system 回報 12.35% 訊號 LONG" in prompt
    assert "bigline 回報 9.88% 訊號 SHORT" in prompt


def test_generate_script_fallback_retains_strategy_summary(monkeypatch):
    monkeypatch.setattr(cc, "generate_script_with_llm", lambda prompt: None)

    strategy_results = {
        "QQQ": {
            "strategy": "bigline",
            "expected_return": 7.891,
            "signals": {"position": "LONG"},
            "strategies": {
                "god_system": _strategy_result(6.0, "SHORT"),
                "bigline": _strategy_result(7.891, "LONG"),
            },
        }
    }

    fallback = cc.generate_script(
        {"market": {"QQQ": {"close": 380, "change": -0.4}}, "news": [], "sentiment": {"overall_score": 0.2, "bullish_ratio": 0.45}},
        "us",
        strategy_results,
        {"QQQ": {"trend": "DOWN", "volatility": 3.1, "report": "Volatility rising"}},
    )

    assert "QQQ: 最佳策略 bigline，預期回報 7.89%，訊號 LONG。" in fallback
    assert "bigline 回報 7.89% 訊號 LONG" in fallback
    assert "god_system 回報 6.00% 訊號 SHORT" in fallback
