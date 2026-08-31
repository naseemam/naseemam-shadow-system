from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "06_Code" / "kernel"


def _load(name: str):
    spec = util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_shadow_system_structure_keeps_projects_and_admin_separate():
    mod = _load("shadow_system_structure")
    assert mod.MAIN_NAVIGATION == (
        "home", "friendly_chat", "business_chat", "customer_supervision", "projects", "administration"
    )
    assert {"hilm_alnada", "school", "trading"}.issubset(mod.PROJECTS)
    assert "system_and_connector_health" in mod.ADMINISTRATION
    contract = mod.shadow_system_contract()
    assert contract.project_gateway_is_router_not_competing_brain is True
    assert contract.customer_supervision_is_projection_not_duplicate_source is True
    assert contract.approvals_only_for_preclassified_sovereign_decisions is True


def test_connector_orchestration_is_centralized_under_ameer():
    mod = _load("connector_orchestration")
    contract = mod.connector_orchestration_contract()
    assert contract.operational_owner == "ameer"
    assert contract.centralized_registry is True
    assert contract.project_gateway_enforces_project_isolation is True
    assert contract.secret_values_forbidden_in_execution_logs is True
    assert contract.ameer_may_refresh_and_rotate_operational_tokens is True
    assert "trading_platforms" in mod.CONNECTOR_CLASSES
    assert "investment_funds" in mod.CONNECTOR_CLASSES
    assert "whatsapp" in mod.CONNECTOR_CLASSES
    assert "tiktok" in mod.CONNECTOR_CLASSES


def test_trading_autonomy_prioritizes_capital_protection_without_per_trade_approval():
    mod = _load("trading_autonomy")
    contract = mod.trading_autonomy_contract()
    assert contract.per_trade_founder_approval_required is False
    assert contract.capital_protection_priority is True
    assert contract.may_exit_before_large_loss_when_risk_signals_trigger is True
    assert contract.prediction_is_probabilistic_not_certain is True
    assert contract.continuous_skill_learning is True
    assert "trailing_stop_exit" in mod.AUTONOMOUS_TRADING_ACTIONS
    assert "rapid_drawdown_detection" in mod.RISK_CONTROLS
    assert "backtest" in mod.LEARNING_LOOP


def test_central_authority_exempts_only_delegated_trades_inside_scope():
    auth = _load("ameer_authority")
    delegated = {
        "delegated_trading_execution": True,
        "actor": "trading_bot",
        "within_authorized_trading_account": True,
        "within_trading_risk_policy": True,
    }
    assert auth.requires_founder_approval("sell", delegated) is False
    assert auth.requires_founder_approval("buy", delegated) is False

    outside_risk = dict(delegated, within_trading_risk_policy=False)
    assert auth.requires_founder_approval("payment", outside_risk) is True

    withdrawal = dict(delegated, withdrawal=True, operation_kind="sell")
    assert auth.requires_founder_approval("payment", withdrawal) is True


def test_customer_checkout_is_not_founder_business_spend():
    auth = _load("ameer_authority")
    assert auth.requires_founder_approval(
        "payment",
        {"ordinary_customer_checkout": True, "customer_self_payment": True, "actual_funds_movement": True},
    ) is False
    assert auth.requires_founder_approval(
        "payment",
        {"business_spend": True, "actual_funds_movement": True},
    ) is True

    checkout = _load("checkout_payment_architecture").checkout_payment_contract()
    assert checkout.ordinary_customer_payment_requires_founder_approval is False
    assert checkout.founder_financial_gate_applies_to_business_spend_not_customer_checkout is True
