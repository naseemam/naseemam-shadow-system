from kernel.business_capability_domains import business_capability_snapshot, customer_journey_worker_contract


def test_office_and_school_artifacts_are_first_class_capabilities():
    snap = business_capability_snapshot()
    artifacts = set(snap["artifact_generation"])
    assert {"spreadsheet_xlsx", "word_docx", "pdf", "presentation_pptx", "school_records", "inventory_records", "employee_records"}.issubset(artifacts)


def test_high_quality_media_is_first_class_capability():
    media = set(business_capability_snapshot()["media_generation"])
    assert "high_quality_image_generation" in media
    assert "high_quality_video_generation" in media
    assert "social_media_creatives" in media


def test_hilm_alnada_operational_domains_cover_store_inventory_and_bookings():
    ops = set(business_capability_snapshot()["commerce_operations"])
    assert {"website_content_management", "store_management", "inventory_management", "booking_management", "service_catalog_management", "offer_management"}.issubset(ops)


def test_tiktok_can_be_planned_generated_and_published_when_connector_exists():
    ops = set(business_capability_snapshot()["social_operations"])
    assert "tiktok_content_planning" in ops
    assert "tiktok_media_generation" in ops
    assert "tiktok_publishing_when_connector_available" in ops


def test_customer_journey_has_specialist_worker_contract_end_to_end():
    contract = customer_journey_worker_contract()
    assert contract["worker_role"] == "customer_journey_specialist"
    assert contract["stages"][0] == "discovery"
    assert "checkout" in contract["stages"]
    assert "purchase_confirmation" in contract["stages"]
    assert contract["may_recommend_services"] is True
    assert contract["may_coordinate_bookings"] is True
    assert contract["may_propose_and_execute_operational_improvements"] is True
