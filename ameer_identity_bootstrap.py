from kernel.provider_identity_patch import install_provider_identity_patch

# Install identity ownership before the executive kernel is constructed.
install_provider_identity_patch()

from ameer_delivery_bootstrap import app  # noqa: E402,F401
