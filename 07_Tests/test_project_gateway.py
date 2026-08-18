from pathlib import Path

from kernel.central_audit import CentralExecutionAudit
from kernel.project_gateway import ProjectGateway
from kernel.shadow_foundation import ShadowFoundation


def make_gateway(tmp_path: Path) -> ProjectGateway:
    foundation = ShadowFoundation(tmp_path)
    audit = CentralExecutionAudit(tmp_path)
    return ProjectGateway(foundation, audit=audit)


def test_gateway_allows_ameer_read_inside_project(tmp_path: Path):
    gateway = make_gateway(tmp_path)
    result = gateway.route_to_ameer(
        subject_id="ameer",
        role_id="ameer",
        project_id="dream_al_nada",
        capability="project.read",
        action="read",
        context={"project_id": "dream_al_nada"},
    )
    assert result["allowed"] is True
    assert result["route"]["via"] == "ameer"
    assert result["route"]["direct_worker_access"] is False


def test_gateway_blocks_cross_project_context(tmp_path: Path):
    gateway = make_gateway(tmp_path)
    result = gateway.authorize(
        subject_id="ameer",
        role_id="ameer",
        project_id="school",
        capability="project.read",
        action="read",
        context={"project_id": "trading"},
    )
    assert result["allowed"] is False
    assert result["reason"] == "cross_project_context_denied"


def test_gateway_blocks_customer_from_internal_admin(tmp_path: Path):
    gateway = make_gateway(tmp_path)
    gateway.foundation.assign("customer-1", "customer", "dream_al_nada_store")
    result = gateway.authorize(
        subject_id="customer-1",
        role_id="customer",
        project_id="dream_al_nada_admin",
        capability="project.read",
        action="read",
    )
    assert result["allowed"] is False
    assert result["reason"] == "no_project_assignment"


def test_gateway_keeps_trading_execution_disabled(tmp_path: Path):
    gateway = make_gateway(tmp_path)
    result = gateway.authorize(
        subject_id="ameer",
        role_id="ameer",
        project_id="trading",
        capability="trading.execute",
        action="external_effect",
        worker_id="operations",
    )
    assert result["allowed"] is False
    assert result["reason"] == "policy_denied"
