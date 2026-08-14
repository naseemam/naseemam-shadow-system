from kernel.provider_identity_patch import install_provider_identity_patch

# Install identity ownership before the executive kernel is constructed.
install_provider_identity_patch()

from ameer_delivery_bootstrap import app  # noqa: E402,F401
from kernel.execution_bridge_patch import install_execution_bridge_patch  # noqa: E402

# The delivery kernel is now constructed; bridge natural Founder language into
# its executable task decomposer so understood commands do not remain talk-only.
install_execution_bridge_patch()
