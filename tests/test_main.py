import copy
import os
from pathlib import Path

import pandas as pd
import pytest

import main as main_module


def _make_strategy_class(name, payloads):
    class _Strategy:
        calls = []

        def __init__(self, config):
            self.config = config

        def backtest(self, symbol, df, timeframe="daily"):
            _Strategy.calls.append(
                {
                    "strategy": name,
                    "symbol": symbol,
                    "sentiments": tuple(df["sentiment_score"].unique()),
                    "timeframe": timeframe,
                }
            )
            result = payloads[symbol]
            return {
                "expected_return": result["expected_return"],
                "max_drawdown": result["max_drawdown"],
                "sharpe_ratio": result["sharpe_ratio"],
                "signals": {"position": result["position"]},
            }

    return _Strategy


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_copy = copy.deepcopy(main_module.config)
    podcast_root = tmp_path / "podcasts"
    market_root = tmp_path / "market"
    config_copy["data_paths"] = copy.deepcopy(main_module.config["data_paths"])
    config_copy["data_paths"]["podcast"] = str(podcast_root)
    config_copy["data_paths"]["market"] = str(market_root)
    monkeypatch.setattr(main_module, "config", config_copy, raising=False)
    return config_copy


def test_main_aggregates_dual_strategy_metrics(tmp_path, monkeypatch, temp_config):
    market_dir = Path(temp_config["data_paths"]["market"])
    market_dir.mkdir(parents=True, exist_ok=True)

    for symbol in ("SPY", "QQQ"):
        df = pd.DataFrame(
            {
                "date": pd.date_range(start="2024-01-01", periods=3, tz="UTC"),
                "open": [100, 101, 102],
                "high": [101, 102, 103],
                "low": [99, 100, 101],
                "close": [100, 102, 104],
                "change": [0.0, 1.5, 2.0],
                "volume": [1_000_000, 1_100_000, 1_200_000],
            }
        )
        df.to_csv(market_dir / f"daily_{symbol}.csv", index=False)

    fake_market_data = {
        "market": {
            "SPY": {"close": 100.0, "change": 1.2},
            "QQQ": {"close": 200.0, "change": -0.3},
        },
        "sentiment": {
            "overall_score": 0.25,
            "symbols": {
                "SPY": {"sentiment_score": 0.8},
            },
        },
        "news": [],
    }

    def fake_collect_data(mode):
        assert mode == "us"
        return fake_market_data

    god_payloads = {
        "SPY": {
            "expected_return": 0.5,
            "max_drawdown": 0.1,
            "sharpe_ratio": 1.4,
            "position": "LONG",
        },
        "QQQ": {
            "expected_return": 0.2,
            "max_drawdown": 0.15,
            "sharpe_ratio": 1.1,
            "position": "SHORT",
        },
    }
    big_payloads = {
        "SPY": {
            "expected_return": 0.3,
            "max_drawdown": 0.05,
            "sharpe_ratio": 1.2,
            "position": "FLAT",
        },
        "QQQ": {
            "expected_return": 0.4,
            "max_drawdown": 0.2,
            "sharpe_ratio": 1.3,
            "position": "LONG",
        },
    }

    GodStub = _make_strategy_class("god_system", god_payloads)
    BigStub = _make_strategy_class("bigline", big_payloads)
    GodStub.calls = []
    BigStub.calls = []

    captured = {}

    def fake_generate_script(market_data, mode, strategy_results, market_analysis):
        captured["strategy_results"] = strategy_results
        captured["market_analysis"] = market_analysis
        return "script text"

    def fake_generate_audio(script_path, audio_path):
        assert os.path.exists(script_path)
        Path(audio_path).parent.mkdir(parents=True, exist_ok=True)

    def fake_upload_episode(today, mode, files):
        captured["upload"] = {"today": today, "mode": mode, "files": files}
        return {"audio": f"https://example.com/{today}/{mode}.mp3"}

    def fake_generate_rss(today, mode, script, audio_url, strategy_results):
        captured["rss"] = {
            "today": today,
            "mode": mode,
            "audio_url": audio_url,
            "strategy_results": strategy_results,
        }

    class FakeAnalyst:
        def __init__(self, config):
            self.config = config

        def analyze_market(self, symbol):
            return {"trend": "UP", "volatility": 4.2, "report": f"{symbol} outlook"}

    monkeypatch.setattr(main_module, "collect_data", fake_collect_data)
    monkeypatch.setattr(main_module, "GodSystemStrategy", GodStub)
    monkeypatch.setattr(main_module, "BigLineStrategy", BigStub)
    monkeypatch.setattr(main_module, "generate_script", fake_generate_script)
    monkeypatch.setattr(main_module, "generate_audio", fake_generate_audio)
    monkeypatch.setattr(main_module, "upload_episode", fake_upload_episode)
    monkeypatch.setattr(main_module, "generate_rss", fake_generate_rss)
    monkeypatch.setattr(main_module, "MarketAnalyst", FakeAnalyst)

    main_module.main("us")

    # Two strategies should be invoked per symbol with correct sentiment injection.
    assert {(call["strategy"], call["symbol"]) for call in GodStub.calls} == {
        ("god_system", "SPY"),
        ("god_system", "QQQ"),
    }
    assert {(call["strategy"], call["symbol"]) for call in BigStub.calls} == {
        ("bigline", "SPY"),
        ("bigline", "QQQ"),
    }

    def lookup_sentiment(calls, strategy_name, symbol):
        for call in calls:
            if call["strategy"] == strategy_name and call["symbol"] == symbol:
                return call["sentiments"]
        raise AssertionError(f"No call recorded for {strategy_name} / {symbol}")

    assert lookup_sentiment(GodStub.calls, "god_system", "SPY") == (0.8,)
    assert lookup_sentiment(BigStub.calls, "bigline", "QQQ") == (0.25,)

    strategy_results = captured["strategy_results"]
    assert set(strategy_results.keys()) == {"SPY", "QQQ"}
    assert strategy_results["SPY"]["strategy"] == "god_system"
    assert strategy_results["SPY"]["strategies"]["god_system"]["signals"]["position"] == "LONG"
    assert strategy_results["SPY"]["strategies"]["bigline"]["signals"]["position"] == "FLAT"
    assert strategy_results["QQQ"]["strategy"] == "bigline"
    assert strategy_results["QQQ"]["strategies"]["bigline"]["expected_return"] == pytest.approx(0.4)

    # Market analysis should mirror FakeAnalyst output.
    assert captured["market_analysis"]["SPY"]["report"] == "SPY outlook"
    assert captured["market_analysis"]["QQQ"]["trend"] == "UP"

    # RSS and upload phases receive the per-strategy detail.
    assert captured["rss"]["strategy_results"] == strategy_results
    assert "audio" in captured["upload"]["files"]
