"""Delegated autonomous trading policy for Ameer and the trading bot.

Trading execution inside the Founder-authorized account is a specific delegated
exception to the general financial sovereign gate. Ameer and the trading bot may
buy, sell, open, close, reduce, rebalance, and exit positions without per-trade
Founder approval while remaining inside configured account and risk boundaries.

This module does not promise prediction certainty. Signals are probabilistic and
capital protection has priority over waiting for a hoped-for recovery.
"""

from dataclasses import dataclass
from typing import Tuple

AUTONOMOUS_TRADING_ACTIONS: Tuple[str, ...] = (
    "buy",
    "sell",
    "open_position",
    "close_position",
    "reduce_position",
    "rebalance_position",
    "stop_loss_exit",
    "trailing_stop_exit",
    "emergency_risk_exit",
    "cancel_or_replace_order",
)

MARKET_OBSERVATIONS: Tuple[str, ...] = (
    "price",
    "volume",
    "liquidity",
    "spread",
    "volatility",
    "candlestick_structure",
    "trend",
    "momentum",
    "support_and_resistance",
    "gap_and_breakout_behavior",
    "portfolio_exposure",
    "market_regime",
)

RISK_CONTROLS: Tuple[str, ...] = (
    "maximum_position_size",
    "maximum_total_exposure",
    "daily_loss_limit",
    "stop_loss",
    "trailing_stop",
    "volatility_adjusted_exit",
    "rapid_drawdown_detection",
    "liquidity_and_spread_guard",
    "position_concentration_limit",
    "emergency_trading_halt",
)

LEARNING_LOOP: Tuple[str, ...] = (
    "observe_market_and_execution_results",
    "identify_strategy_limitations",
    "research_trading_and_market_skills",
    "evaluate_candidate_signal_or_strategy",
    "backtest",
    "paper_or_sandbox_test_when_supported",
    "compare_against_baseline",
    "adopt_or_reject",
    "monitor_live_performance",
    "improve_reduce_or_retire_strategy",
)

TRADE_DECISION_RECORD: Tuple[str, ...] = (
    "strategy_id",
    "instrument",
    "signal_timestamp",
    "entry_or_exit_reason",
    "observed_market_state",
    "risk_state",
    "order_type",
    "requested_price",
    "filled_price",
    "position_size",
    "fees_and_slippage",
    "realized_pnl",
    "post_trade_outcome",
    "strategy_evaluation_reference",
)


@dataclass(frozen=True)
class TradingAutonomyContract:
    authorized_actors: Tuple[str, ...] = ("ameer", "trading_bot")
    per_trade_founder_approval_required: bool = False
    authorized_account_scope_required: bool = True
    configured_risk_policy_required: bool = True
    capital_protection_priority: bool = True
    may_exit_before_large_loss_when_risk_signals_trigger: bool = True
    may_use_dynamic_stop_loss: bool = True
    may_use_trailing_stop: bool = True
    may_reduce_position_before_full_exit: bool = True
    prediction_is_probabilistic_not_certain: bool = True
    continuous_market_monitoring: bool = True
    continuous_skill_learning: bool = True
    backtest_before_strategy_adoption: bool = True
    live_performance_monitoring: bool = True
    decision_evidence_required: bool = True
    external_withdrawal_is_not_trading_execution: bool = True
    ownership_change_is_not_trading_execution: bool = True
    unrelated_business_spend_is_not_trading_execution: bool = True


def trading_autonomy_contract() -> TradingAutonomyContract:
    return TradingAutonomyContract()
