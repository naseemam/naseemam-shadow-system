from kernel.domain_surface_routing import (
    HILM_PUBLIC_HOST,
    MOTHER_HOST,
    SCHOOL_PUBLIC_HOST,
    deployment_readiness,
    normalize_host,
    route_for_host,
)


def test_canonical_hosts_have_expected_visibility():
    assert route_for_host(MOTHER_HOST).visibility == "private"
    assert route_for_host(MOTHER_HOST).requires_auth is True
    assert route_for_host(HILM_PUBLIC_HOST).visibility == "public"
    assert route_for_host(HILM_PUBLIC_HOST).requires_auth is False
    assert route_for_host(SCHOOL_PUBLIC_HOST).visibility == "public"
    assert route_for_host(SCHOOL_PUBLIC_HOST).requires_auth is False


def test_unknown_host_fails_closed():
    route = route_for_host("random.ameernas.com")
    assert route.visibility == "private"
    assert route.requires_auth is True
    assert route.surface == "unknown_private"


def test_host_normalization_handles_www_port_and_case():
    assert normalize_host("WWW.AMEERNAS.COM:443") == "ameernas.com"


def test_readiness_never_claims_dns_cutover_complete():
    readiness = deployment_readiness()
    assert readiness["dns_cutover_authorized"] is False
    assert readiness["mother"]["auth_required"] is True
