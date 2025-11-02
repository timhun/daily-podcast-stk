import podcast_distributor as pd_module


def sample_strategy_result(best_name="god_system"):
    return {
        "strategy": "fallback",
        "expected_return": 1.23,
        "signals": {"position": "NEUTRAL"},
        "best": {
            "name": best_name,
            "expected_return": 2.5,
            "signals": {"position": "LONG"},
        },
        "strategies": {
            "god_system": {"expected_return": 2.5, "signals": {"position": "LONG"}},
            "bigline": {"expected_return": 1.1, "signals": {"position": "SHORT"}},
        },
    }


def test_summarize_symbol_strategy_surfaces_best_and_details():
    summary = pd_module.summarize_symbol_strategy("QQQ", sample_strategy_result("bigline"))
    assert summary["symbol"] == "QQQ"
    assert summary["best_name"] == "bigline"
    assert summary["best_position"] == "LONG"
    assert summary["best_return"] == 2.5
    # Detail should list both strategies
    assert "bigline SHORT 1.10%" in summary["detail"]
    assert "god_system LONG 2.50%" in summary["detail"]


def test_build_strategy_digest_formats_multiline_overview():
    digest = pd_module.build_strategy_digest(
        {"QQQ": sample_strategy_result("god_system"), "SPY": sample_strategy_result("bigline")}
    )
    assert "QQQ 最佳 god_system（LONG，2.50%）" in digest
    assert "SPY 最佳 bigline（LONG，2.50%）" in digest
    assert "god_system LONG 2.50%" in digest
    assert "bigline SHORT 1.10%" in digest
