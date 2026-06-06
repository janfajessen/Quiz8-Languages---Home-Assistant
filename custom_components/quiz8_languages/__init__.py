"""Quiz8 Languages integration for Home Assistant."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, PLATFORMS, SUPPORTED_LANGUAGES
from .coordinator import Quiz8LanguagesCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_REGISTER_ANSWER = "register_answer"
SERVICE_COMPLETE_ROUND  = "complete_round"
SERVICE_SET_LANGUAGE    = "set_active_language"
SERVICE_MARK_DAY_PLAYED = "mark_day_played"

SCHEMA_REGISTER_ANSWER = vol.Schema({
    vol.Required("language"): vol.In(list(SUPPORTED_LANGUAGES.keys())),
    vol.Required("word_id"):  cv.string,
    vol.Required("correct"):  cv.boolean,
})
SCHEMA_COMPLETE_ROUND = vol.Schema({
    vol.Required("language"): vol.In(list(SUPPORTED_LANGUAGES.keys())),
})
SCHEMA_SET_LANGUAGE = vol.Schema({
    vol.Required("language"): vol.In(list(SUPPORTED_LANGUAGES.keys())),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Quiz8 Languages from a config entry."""
    coordinator = Quiz8LanguagesCoordinator(hass, entry)
    await coordinator.async_setup()

    # Poblar data ANTES de registrar sensores
    coordinator.data = coordinator._build_state()

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("First refresh failed, using initial state: %s", err)

    if coordinator.data is None:
        coordinator.data = coordinator._build_state()

    _LOGGER.info(
        "Quiz8 Languages loaded — %d languages, active: %s",
        len(coordinator.selected_languages),
        coordinator.data.get("active_language") if coordinator.data else None,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Registrar sensores después de garantizar data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass, coordinator)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            for service in [
                SERVICE_REGISTER_ANSWER,
                SERVICE_COMPLETE_ROUND,
                SERVICE_SET_LANGUAGE,
                SERVICE_MARK_DAY_PLAYED,
            ]:
                hass.services.async_remove(DOMAIN, service)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant, coordinator: Quiz8LanguagesCoordinator) -> None:
    """Register HA services."""

    async def handle_register_answer(call: ServiceCall) -> None:
        coordinator.register_answer(
            lang=call.data["language"],
            word_id=call.data["word_id"],
            correct=call.data["correct"],
        )
        await coordinator.async_refresh()

    async def handle_complete_round(call: ServiceCall) -> None:
        coordinator.complete_round(lang=call.data["language"])
        await coordinator.async_refresh()

    async def handle_set_language(call: ServiceCall) -> None:
        coordinator.set_active_language(lang=call.data["language"])
        await coordinator.async_refresh()

    async def handle_mark_day_played(call: ServiceCall) -> None:
        await coordinator.async_mark_day_played()
        await coordinator.async_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_REGISTER_ANSWER):
        hass.services.async_register(DOMAIN, SERVICE_REGISTER_ANSWER, handle_register_answer, schema=SCHEMA_REGISTER_ANSWER)
        hass.services.async_register(DOMAIN, SERVICE_COMPLETE_ROUND,  handle_complete_round,  schema=SCHEMA_COMPLETE_ROUND)
        hass.services.async_register(DOMAIN, SERVICE_SET_LANGUAGE,    handle_set_language,    schema=SCHEMA_SET_LANGUAGE)
        hass.services.async_register(DOMAIN, SERVICE_MARK_DAY_PLAYED, handle_mark_day_played, schema=vol.Schema({}))

    _LOGGER.debug("Quiz8 Languages services registered")
    