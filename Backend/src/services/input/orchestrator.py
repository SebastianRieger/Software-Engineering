from datetime import datetime
import logging
import time
import threading
from collections.abc import Callable
from typing import Any

from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.commands import CommandProfile
from schemas.interactions import InputActionConfig, InputSourceType, UIActionArguments


logger = logging.getLogger(__name__)


def _model_to_dict(model_or_dict: UIActionArguments | dict[str, Any] | None) -> dict[str, Any]:
    if model_or_dict is None:
        return {}
    if isinstance(model_or_dict, UIActionArguments):
        return model_or_dict.model_dump(exclude_none=True)
    return UIActionArguments.model_validate(model_or_dict).model_dump(exclude_none=True)


class InputOrchestrator:
    def __init__(
        self,
        realtime: RealtimeHub | None = None,
        config_repository_factory: Callable[[], ConfigRepository] | type[ConfigRepository] | None = None,
    ) -> None:
        self.realtime = realtime or realtime_hub
        self.config_repository_factory = config_repository_factory or ConfigRepository
        self._lock = threading.RLock()
        self._input_action_config = InputActionConfig()
        self._active_command_profile: CommandProfile | None = None
        self._last_action_at = 0.0
        self._last_action_priority = 0
        self._last_action_time_by_name: dict[str, float] = {}

    def reload_config(self) -> InputActionConfig:
        try:
            repository = self.config_repository_factory()
            config = repository.get_input_action_config()
            active_profile_getter = getattr(repository, "get_active_command_profile", None)
            active_profile = active_profile_getter() if callable(active_profile_getter) else None
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            logger.warning("Could not reload input action config, using defaults: %s", exc)
            config = InputActionConfig()
            active_profile = None

        with self._lock:
            self._input_action_config = config
            self._active_command_profile = active_profile
        return config

    def publish_raw_input_detected(
        self,
        *,
        input_source: InputSourceType,
        raw_input: str,
        timestamp: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.realtime.publish_from_thread(
            {
                "eventType": "RawInputDetected",
                "payload": {
                    "input_source": input_source,
                    "raw_input": raw_input,
                    "timestamp": timestamp.isoformat(),
                    "metadata": metadata or {},
                },
            }
        )

    def publish_command_match_evaluated(
        self,
        *,
        input_source: InputSourceType,
        raw_input: str,
        timestamp: datetime,
        outcome: str,
        action: str | None = None,
        reason: str | None = None,
        action_args: UIActionArguments | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.realtime.publish_from_thread(
            {
                "eventType": "CommandMatchEvaluated",
                "payload": {
                    "input_source": input_source,
                    "raw_input": raw_input,
                    "timestamp": timestamp.isoformat(),
                    "outcome": outcome,
                    "action": action,
                    "reason": reason,
                    "action_args": _model_to_dict(action_args),
                    "metadata": metadata or {},
                },
            }
        )

    def publish_ui_action_requested(
        self,
        *,
        input_source: InputSourceType,
        raw_input: str,
        timestamp: datetime,
        action_args: UIActionArguments | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        with self._lock:
            mappings = list(self._input_action_config.mappings)
            active_profile = self._active_command_profile

        merged_metadata = metadata or {}
        merged_action_args = _model_to_dict(action_args)

        if active_profile is not None:
            modality_settings = active_profile.modality_settings.get(input_source)
            if modality_settings is not None and not modality_settings.enabled:
                self.publish_command_match_evaluated(
                    input_source=input_source,
                    raw_input=raw_input,
                    timestamp=timestamp,
                    outcome="disabled",
                    reason="modality_disabled",
                    action_args=merged_action_args,
                    metadata=merged_metadata,
                )
                return False

        mapping = next(
            (
                item
                for item in mappings
                if item.enabled and item.input_source == input_source and item.raw_input == raw_input
            ),
            None,
        )
        if mapping is None:
            self.publish_command_match_evaluated(
                input_source=input_source,
                raw_input=raw_input,
                timestamp=timestamp,
                outcome="unmapped",
                reason="no_mapping",
                action_args=merged_action_args,
                metadata=merged_metadata,
            )
            return False

        merged_action_args = {
            **_model_to_dict(mapping.action_args),
            **merged_action_args,
        }

        merged_metadata = {
            **mapping.metadata,
            **merged_metadata,
        }

        now = time.monotonic()
        with self._lock:
            global_cooldown_seconds = self._input_action_config.global_cooldown_seconds
            repeat_same_action_window_seconds = self._input_action_config.repeat_same_action_window_seconds
            source_priorities = dict(self._input_action_config.source_priorities)
            current_priority = source_priorities.get(mapping.input_source, 0)
            last_same_action_at = self._last_action_time_by_name.get(mapping.action, 0.0)

            if now - last_same_action_at < repeat_same_action_window_seconds:
                self.publish_command_match_evaluated(
                    input_source=input_source,
                    raw_input=raw_input,
                    timestamp=timestamp,
                    outcome="suppressed",
                    action=mapping.action,
                    reason="repeat_window",
                    action_args=merged_action_args,
                    metadata=merged_metadata,
                )
                return False

            if now - self._last_action_at < global_cooldown_seconds and current_priority <= self._last_action_priority:
                self.publish_command_match_evaluated(
                    input_source=input_source,
                    raw_input=raw_input,
                    timestamp=timestamp,
                    outcome="suppressed",
                    action=mapping.action,
                    reason="global_cooldown",
                    action_args=merged_action_args,
                    metadata=merged_metadata,
                )
                return False

            self._last_action_at = now
            self._last_action_priority = current_priority
            self._last_action_time_by_name[mapping.action] = now

        self.publish_command_match_evaluated(
            input_source=input_source,
            raw_input=raw_input,
            timestamp=timestamp,
            outcome="accepted",
            action=mapping.action,
            action_args=merged_action_args,
            metadata=merged_metadata,
        )

        self.realtime.publish_from_thread(
            {
                "eventType": "UIActionRequested",
                "payload": {
                    "action": mapping.action,
                    "timestamp": timestamp.isoformat(),
                    "input_source": input_source,
                    "raw_input": raw_input,
                    "action_args": merged_action_args,
                    "metadata": merged_metadata,
                },
            }
        )
        return True


input_orchestrator = InputOrchestrator()