"""First-class artifact generation capabilities for Ameer.

Ameer may choose the best available worker/model/toolchain to produce requested
artifacts. Providers are replaceable execution resources; artifact capability is
owned by Ameer's orchestration layer, not by any single external model.

The target is end-to-end delivery: interpret the request, inspect source material,
choose tools, generate, validate, repair, render/export, and deliver the result.
"""

from __future__ import annotations


ARTIFACT_CAPABILITIES = {
    "image_generation": {
        "outputs": ["png", "jpg", "webp"],
        "quality_target": "high_quality",
        "workflow": ["understand", "generate", "inspect", "refine", "deliver"],
    },
    "video_generation": {
        "outputs": ["mp4", "webm"],
        "quality_target": "high_quality",
        "workflow": ["concept", "storyboard", "generate", "assemble", "quality_check", "refine", "deliver"],
    },
    "presentations": {
        "outputs": ["pptx", "pdf"],
        "workflow": ["structure", "design", "build", "render_check", "repair", "deliver"],
    },
    "documents": {
        "outputs": ["docx", "pdf", "md", "txt"],
        "workflow": ["draft", "format", "validate", "deliver"],
    },
    "spreadsheets": {
        "outputs": ["xlsx", "csv"],
        "workflow": ["model", "build", "formula_check", "visual_check", "deliver"],
    },
    "code": {
        "outputs": ["source", "patch", "repository_change", "build_artifact"],
        "workflow": ["inspect", "design", "edit", "test", "repair", "retest", "deliver"],
    },
    "web_ui": {
        "outputs": ["html", "css", "js", "framework_components", "deployed_preview"],
        "workflow": ["inspect", "design", "build", "run", "visual_check", "repair", "deliver"],
    },
}


def artifact_capability(name: str) -> dict:
    return dict(ARTIFACT_CAPABILITIES.get(name, {}))


def artifact_policy_snapshot() -> dict:
    return {
        "artifact_generation_is_first_class": True,
        "capabilities": ARTIFACT_CAPABILITIES,
        "provider_independent": True,
        "ameer_selects_toolchain": True,
        "end_to_end_delivery": True,
        "validation_and_repair_required": True,
        "external_models_are_replaceable_resources": True,
    }
