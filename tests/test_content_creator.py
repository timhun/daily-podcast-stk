"""Prompt 合約測試：US 舊路徑不變、TW 走 template_tw_v1 掛載。"""

import content_creator as cc


def _strategy_result(expected, position):
    return {
        "expected_return": expected,
        "max_drawdown": 0.1,
        "sharpe_ratio": 1.2,
        "signals": {"position": position},
    }


def _capture_llm(monkeypatch, result="LLM output"):
    """替身 LLM：攔下 prompt/system/min_chars，避開網路與評分器副作用。"""
    captured = {}

    def fake(prompt, system_prompt=None, min_chars=None):
        captured.update(prompt=prompt, system=system_prompt, min_chars=min_chars)
        return result

    monkeypatch.setattr(cc, "generate_script_with_llm", fake)
    monkeypatch.setattr(cc, "post_gen_eval", lambda mode, script: None)
    return captured


# ── US 舊路徑（回歸保護：TW 改動不得波及 US） ─────────────────────


def test_generate_script_prompt_captures_dual_strategy_summary(monkeypatch):
    captured = _capture_llm(monkeypatch)

    strategy_results = {
        "QQQ": {
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
        "market": {"QQQ": {"close": 500, "change": 1.25}},
        "news": [],
        "sentiment": {"overall_score": 0.4, "bullish_ratio": 0.6},
    }

    result = cc.generate_script(
        market_data,
        "us",
        strategy_results,
        {"QQQ": {"trend": "UP", "volatility": 2.5, "report": "Solid momentum"}},
    )
    assert result == "LLM output"

    prompt = captured["prompt"]
    # 策略摘要（只取 god_system/MA20，bigline 不得露名）進 prompt
    assert "科技股ETF訊號「多方」，建議分批布局" in prompt
    assert "12.35%" in prompt
    assert "bigline" not in prompt
    # 技術面摘要也進 prompt
    assert "Solid momentum" in prompt
    # US 仍走舊 system（AI 新聞 70/30 規格）與 2,500 字門檻
    assert captured["system"] == cc._get_sys("us")
    assert captured["min_chars"] == cc.MIN_CHARS


def test_generate_script_fallback_retains_strategy_summary(monkeypatch):
    monkeypatch.setattr(
        cc, "generate_script_with_llm", lambda prompt, **kwargs: None
    )

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
        {
            "market": {"QQQ": {"close": 380, "change": -0.4}},
            "news": [],
            "sentiment": {"overall_score": 0.2, "bullish_ratio": 0.45},
        },
        "us",
        strategy_results,
        {"QQQ": {"trend": "DOWN", "volatility": 3.1, "report": "Volatility rising"}},
    )

    # god_system（MA20）空方 → 空方操作建議進 fallback；bigline 不得露名
    assert "建議觀望或減碼控制風險" in fallback
    assert "bigline" not in fallback
    assert "Kostolany" in fallback


# ── template_tw_v1 掛載（本次工單核心） ────────────────────────────


def test_tw_system_prompt_is_template_v1_not_legacy_ai_news():
    sysp = cc._tw_system_prompt()
    # 範本檔案全文在 system prompt 裡（單一事實來源）
    template_text = cc._TW_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    assert template_text in sysp
    # 通用禁則併存
    assert "通用禁則" in sysp
    # 舊的 AI 新聞規格不得混入（衝突會讓弱模型混寫兩套規格）
    assert "2500" not in sysp
    assert "70% 內容" not in sysp


def test_tw_template_loader_falls_back_when_file_missing(monkeypatch):
    monkeypatch.setattr(
        cc, "_TW_TEMPLATE_PATH", cc._TW_TEMPLATE_PATH.with_name("no_such_file.md")
    )
    rules = cc._load_tw_template_rules()
    assert rules == cc._TW_TEMPLATE_FALLBACK
    # 內嵌備援本身仍要是範本骨架（不能是空的或舊 AI 新聞規格）
    assert "今日市場定調" in rules
    assert "誠實聲明" in rules
    assert "1,000–1,300" in rules


def test_tw_generate_script_uses_template_prompt(monkeypatch):
    captured = _capture_llm(monkeypatch)

    market = {
        "^TWII": {"close": 36033.29, "change": -6.23, "volume": 0,
                  "timestamp": "2026-11-20"},
        "0050.TW": {"close": 84.45, "change": -6.37, "volume": 791973000},
        "2330.TW": {"close": 2000.0, "change": -4.76, "volume": 88179000},
    }
    result = cc.generate_script(
        {"market": market, "news": [],
         "sentiment": {"overall_score": 0.2, "bullish_ratio": 0.3}},
        "tw", {}, {},
    )
    assert result == "LLM output"

    system = captured["system"]
    prompt = captured["prompt"]

    # system ＝ template_tw_v1 全文＋通用禁則
    template_text = cc._TW_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    assert template_text in system
    assert "通用禁則" in system

    # user prompt：範本骨架、事實資料區、誠實聲明 B、非同日鐵律、免責
    for marker in (
        "1,000–1,300",
        "只准引用以下資料區",
        "誠實聲明 B",
        "非同日，僅供參考",
        "不構成投資建議",
        "【第一部分：大盤收盤紀錄】",
        "收 36,033.29",
        "資料日期 2026-11-20",
    ):
        assert marker in prompt, f"user prompt 缺 {marker!r}"

    # 舊規格（2500 字／70% AI 新聞／AI 投資開場）不得殘留
    assert "2500" not in prompt
    assert "70%" not in prompt
    assert "幫幫幫說AI投資" not in prompt

    # 字數門檻：TW 用範本下限 1,000，不套 2,500 擴展
    assert captured["min_chars"] == 1000


# ── TW 品質閘門（契約＝template_tw_v1，防止優化器朝舊規格漂移） ──


def _template_compliant_script():
    return (
        "各位朋友大家好，我是幫幫忙。今天是 2026 年 11 月 20 日星期五，"
        "這一集的台股收盤。\n\n"
        "今日市場定調：「二次熔斷加速趕底，去槓桿進入深水區」。\n\n"
        "【第一部分：大盤收盤紀錄】加權指數終場大跌 2,393.60 點，收在 36,033.29 點。\n\n"
        "【第二部分：結構與排行】16 檔上漲、1,058 檔下跌，依當日漲跌幅排序。\n\n"
        "【第三部分：權值股】台積電收 2,000 元，下跌 4.8%。\n\n"
        "【第四部分：籌碼與評分（誠實聲明）】11 月 20 日的正式數據還沒有發布。"
        "為了不把不同日期的資料混在一起，今天一律不引用。\n\n"
        "金句：「行情總在絕望中誕生，在懷疑中成長」——科斯托蘭尼。防守為上，輕持股。\n\n"
        "本節目所有輸出僅供個人研究參考，不構成投資建議。\n"
        "（來源標註：價格與結構＝TriLine 正式發布。）"
    )


def test_tw_quality_gate_passes_template_compliant_script():
    diag = cc.validate_quality(_template_compliant_script(), "tw")
    assert diag["pass"] is True, diag
    assert diag["issues"] == []


def test_tw_quality_gate_rejects_legacy_ai_news_script():
    legacy = (
        "歡迎收聽《幫幫幫說AI投資》，我是幫幫忙。RSI 68 顯示多頭略顯過熱。"
        "god_system 訊號多方，建議分批布局。"
    )
    diag = cc.validate_quality(legacy, "tw")
    assert diag["pass"] is False
    # 舊體在新契約下至少缺：段落骨架、金句、免責，且技術指標/策略名洩漏
    labels = " ".join(diag["issues"])
    for key in ("骨架缺失", "金句缺失", "免責缺失", "技術洩漏"):
        assert key in labels, f"舊體應觸發 {key}：{diag}"


def test_tw_quality_gate_flags_missing_disclaimer():
    script = _template_compliant_script().replace("不構成投資建議", "僅供參考")
    diag = cc.validate_quality(script, "tw")
    assert diag["pass"] is False
    assert any("免責缺失" in i for i in diag["issues"])
