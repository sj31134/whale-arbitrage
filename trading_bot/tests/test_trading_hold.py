from unittest.mock import Mock, patch

import pytest

from trading_bot import HOLD_MESSAGE
from trading_bot.core.bot_engine import TradingBotEngine
from trading_bot.execution.order_executor import OrderExecutor


@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("order_type", ["limit", "market"])
def test_order_hold_never_calls_exchange(side, order_type):
    executor = OrderExecutor("", "")
    executor.upbit = Mock()
    result = getattr(executor, f"place_{side}_order")("KRW-TEST", 10, 1, order_type)
    assert result == {"success": False, "error": HOLD_MESSAGE}
    assert executor.upbit.mock_calls == []


def test_hold_prevents_start_and_cancel():
    engine = TradingBotEngine.__new__(TradingBotEngine)
    engine.is_running = False
    with patch("trading_bot.core.bot_engine.threading.Thread") as thread:
        assert engine.start() is False
        assert not engine.is_running
        thread.assert_not_called()
    executor = OrderExecutor("", "")
    executor.upbit = Mock()
    assert executor.cancel_order("fixture") is False
    assert executor.upbit.mock_calls == []


def test_public_page_shows_hold_without_trading_sdk(monkeypatch):
    import sys
    from app.pages.trading_bot_page import render_page

    ui = Mock(session_state={})
    monkeypatch.setitem(sys.modules, "streamlit", ui)
    monkeypatch.setitem(sys.modules, "pyupbit", None)
    render_page()
    ui.info.assert_called_once_with(HOLD_MESSAGE)
    ui.button.assert_not_called()
