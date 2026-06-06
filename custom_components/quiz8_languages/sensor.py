"""Sensor platform for quiz8_languages."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity, SensorEntityDescription, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MASTERY_THRESHOLD, SUPPORTED_LANGUAGES, WORDS_PER_SESSION
from .coordinator import Quiz8LanguagesCoordinator

_LOGGER = logging.getLogger(__name__)

DEVICE_INFO_KWARGS = {
    "name":          "Quiz8 Languages",
    "manufacturer":  "quiz8-languages",
    "model":         "Language Learning Game",
    "sw_version":    "1.0.0",
}


def _d(entity: "Quiz8LanguagesSensor") -> dict[str, Any]:
    return entity.coordinator.data or {}


@dataclass(frozen=True, kw_only=True)
class Quiz8SensorDescription(SensorEntityDescription):
    value_fn: Any = None
    attr_fn:  Any = None


SENSOR_DESCRIPTIONS: tuple[Quiz8SensorDescription, ...] = (
    Quiz8SensorDescription(
        key="score", name="Session Score", icon="mdi:star",
        state_class=SensorStateClass.TOTAL_INCREASING, native_unit_of_measurement="pts",
        value_fn=lambda e: _d(e).get("score", 0),
        attr_fn=lambda e: {"correct_answers": _d(e).get("correct_answers", 0), "wrong_answers": _d(e).get("wrong_answers", 0)},
    ),
    Quiz8SensorDescription(
        key="rounds_completed", name="Rounds Completed", icon="mdi:progress-check",
        state_class=SensorStateClass.TOTAL_INCREASING, native_unit_of_measurement="rounds",
        value_fn=lambda e: _d(e).get("rounds_completed", 0),
        attr_fn=lambda e: {"per_language": {lang: data.get("rounds_done", 0) for lang, data in (_d(e).get("languages", {}) or {}).items()}},
    ),
    Quiz8SensorDescription(
        key="daily_streak", name="Daily Streak", icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="days",
        value_fn=lambda e: _d(e).get("streak", 0),
        attr_fn=lambda e: {},
    ),
    Quiz8SensorDescription(
        key="words_mastered", name="Words Mastered", icon="mdi:brain",
        state_class=SensorStateClass.TOTAL_INCREASING, native_unit_of_measurement="words",
        value_fn=lambda e: _d(e).get("words_mastered_total", 0),
        attr_fn=lambda e: {"per_language": _d(e).get("words_mastered_per_lang", {}), "mastery_threshold": MASTERY_THRESHOLD},
    ),
    Quiz8SensorDescription(
        key="session_accuracy", name="Session Accuracy", icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="%",
        value_fn=lambda e: _d(e).get("accuracy", 0.0),
        attr_fn=lambda e: {"correct": _d(e).get("correct_answers", 0), "wrong": _d(e).get("wrong_answers", 0)},
    ),
    Quiz8SensorDescription(
        key="active_language", name="Active Language", icon="mdi:translate",
        value_fn=lambda e: SUPPORTED_LANGUAGES.get(_d(e).get("active_language", ""), "Unknown"),
        attr_fn=lambda e: {
            "language_code":      _d(e).get("active_language"),
            "ui_language":        _d(e).get("ui_language"),
            "selected_languages": list(e.coordinator.selected_languages),
            "session_date":       _d(e).get("session_date"),
        },
    ),
    Quiz8SensorDescription(
        key="session_progress", name="Session Progress", icon="mdi:book-open-variant",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="words",
        value_fn=lambda e: sum(d.get("pool_index", 0) for d in (_d(e).get("languages", {}) or {}).values()),
        attr_fn=lambda e: {"per_language": {
            lang: {"pool_index": data.get("pool_index", 0), "total": WORDS_PER_SESSION,
                   "percent": round(data.get("pool_index", 0) / WORDS_PER_SESSION * 100)}
            for lang, data in (_d(e).get("languages", {}) or {}).items()
        }},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Quiz8LanguagesCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        Quiz8LanguagesSensor(coordinator, desc) for desc in SENSOR_DESCRIPTIONS
    ]
    # Sensor principal para la tarjeta Lovelace — expone las 24 palabras (3 rondas)
    entities.append(Quiz8LanguageRoundsSensor(coordinator))
    # Sensores por idioma
    for lang_code in coordinator.selected_languages:
        entities.append(Quiz8LanguagePerLangSensor(coordinator, lang_code))
    async_add_entities(entities)


class Quiz8LanguagesSensor(CoordinatorEntity[Quiz8LanguagesCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: Quiz8LanguagesCoordinator, description: Quiz8SensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.entry.entry_id)}, **DEVICE_INFO_KWARGS,
                                            configuration_url="homeassistant://config/integrations")

    @property
    def native_value(self) -> Any:
        try: return self.entity_description.value_fn(self)
        except Exception as err: _LOGGER.debug("value error %s: %s", self.entity_description.key, err); return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        try: return self.entity_description.attr_fn(self) or {}
        except Exception as err: _LOGGER.debug("attr error %s: %s", self.entity_description.key, err); return {}


class Quiz8LanguageRoundsSensor(CoordinatorEntity[Quiz8LanguagesCoordinator], SensorEntity):
    """Expone las 24 palabras (3 rondas × 8) del idioma activo.

    La tarjeta Lovelace lee directamente los atributos de este sensor.
    No se necesitan eventos ni suscripciones WebSocket.
    Se actualiza automáticamente cuando cambia el coordinator.
    """

    _attr_has_entity_name = True
    _attr_name = "Language Rounds"
    _attr_icon = "mdi:cards"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "pairs"

    def __init__(self, coordinator: Quiz8LanguagesCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_language_rounds"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.entry.entry_id)}, **DEVICE_INFO_KWARGS)

    @property
    def native_value(self) -> int:
        data   = self.coordinator.data or {}
        active = data.get("active_language")
        if not active: return 0
        rd = self.coordinator.get_language_rounds(active)
        if not rd: return 0
        return sum(len(r.get("words_left", [])) for r in rd.get("rounds", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data   = self.coordinator.data or {}
        active = data.get("active_language")
        if not active:
            return {"ready": False}
        rd = self.coordinator.get_language_rounds(active)
        if not rd:
            return {"ready": False, "language": active}
        return {
            "ready":       True,
            "language":    rd.get("language"),
            "rounds":      rd.get("rounds", []),       # lista de 3 rondas con words_left, translations_right, word_to_translation
            "ui_language": rd.get("ui_language"),
            "pool_progress": rd.get("pool_progress"),
        }


class Quiz8LanguagePerLangSensor(
    CoordinatorEntity[Quiz8LanguagesCoordinator], SensorEntity
):
    """Per-language progress sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:translate"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "words"

    def __init__(self, coordinator: Quiz8LanguagesCoordinator, lang_code: str) -> None:
        super().__init__(coordinator)
        self._lang_code = lang_code
        lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)
        self._attr_name = f"{lang_name} Progress"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_lang_{lang_code}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)}, **DEVICE_INFO_KWARGS
        )

    @property
    def native_value(self) -> int:
        data = self.coordinator.data or {}
        return data.get("languages", {}).get(self._lang_code, {}).get("pool_index", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data      = self.coordinator.data or {}
        lang_data = data.get("languages", {}).get(self._lang_code, {})
        mastered  = data.get("words_mastered_per_lang", {})
        level     = self.coordinator.language_levels.get(self._lang_code, "A1")
        return {
            "language_code":     self._lang_code,
            "language_name":     SUPPORTED_LANGUAGES.get(self._lang_code, self._lang_code),
            "level":             level,
            "rounds_done_today": lang_data.get("rounds_done", 0),
            "score_today":       lang_data.get("score", 0),
            "pool_index":        lang_data.get("pool_index", 0),
            "pool_total":        WORDS_PER_SESSION,
            "words_mastered":    mastered.get(self._lang_code, 0),
            "mastery_threshold": MASTERY_THRESHOLD,
            "is_active":         data.get("active_language") == self._lang_code,
        }
        