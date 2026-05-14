"""Composable `Settings` field groups (see `science_graphrag.config.Settings`)."""

from science_graphrag.config_mixins.agent_runtime_fields import AgentRuntimeFields
from science_graphrag.config_mixins.core_storage_fields import CoreStorageFields

__all__ = ["AgentRuntimeFields", "CoreStorageFields"]
