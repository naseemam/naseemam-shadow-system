"""Ameer identity belongs to the harness, not to a model provider."""


def harness_identity_policy():
    return {
        "ameer_is_not_model_provider": True,
        "identity_owner": "ameer_harness",
        "memory_owner": "ameer_platform",
        "permissions_owner": "ameer_platform",
        "orchestrator_owner": "ameer_platform",
        "execution_log_owner": "ameer_platform",
        "model_role": "replaceable_inference_engine",
        "provider_role": "replaceable_infrastructure_resource",
        "provider_change_must_not_migrate_identity": True,
        "provider_change_must_not_migrate_memory": True,
        "provider_change_must_not_migrate_permissions": True,
        "local_models_supported_by_contract": True,
        "multiple_providers_supported_by_contract": True,
    }
