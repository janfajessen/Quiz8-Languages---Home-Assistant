"""Config flow for quiz8_languages integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_LANGUAGE_LEVELS,
    CONF_SELECTED_LANGUAGES,
    DOMAIN,
    LEVELS,
    MAX_LANGUAGES_SELECTED,
    RECOMMEND_A1,
    SUPPORTED_LANGUAGES,
)

_LOGGER = logging.getLogger(__name__)


class Quiz8LanguagesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Quiz8 Languages."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._selected_languages: list[str] = []
        self._language_levels: dict[str, str] = {}
        self._current_lang_index: int = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Select exactly 8 languages to learn."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_LANGUAGES, [])
            # cv.multi_select returns a list; we validate length manually
            if len(selected) != MAX_LANGUAGES_SELECTED:
                errors["base"] = "select_exactly_8"
            else:
                self._selected_languages = selected
                self._current_lang_index = 0
                return await self.async_step_level()

        # Build options list: "German (de)", "French (fr)", etc.
        lang_options = {
            code: f"{name} ({code.upper()})"
            for code, name in SUPPORTED_LANGUAGES.items()
        }

        # Use cv.multi_select and enforce exact number of selections
        schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_LANGUAGES): vol.All(
                    cv.multi_select(lang_options),
                    vol.Length(min=MAX_LANGUAGES_SELECTED, max=MAX_LANGUAGES_SELECTED),
                )
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "count": str(MAX_LANGUAGES_SELECTED),
                "total": str(len(SUPPORTED_LANGUAGES)),
            },
        )

    async def async_step_level(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2-9: Set level for each selected language (one per step)."""
        if user_input is not None:
            lang_code = self._selected_languages[self._current_lang_index]
            self._language_levels[lang_code] = user_input["level"]
            self._current_lang_index += 1

        if self._current_lang_index >= len(self._selected_languages):
            # All levels set — create entry
            return self.async_create_entry(
                title="Quiz8 Languages",
                data={
                    CONF_SELECTED_LANGUAGES: self._selected_languages,
                    CONF_LANGUAGE_LEVELS: self._language_levels,
                },
            )

        lang_code = self._selected_languages[self._current_lang_index]
        lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)
        default_level = "A1" if lang_code in RECOMMEND_A1 else "A2"

        schema = vol.Schema(
            {
                vol.Required("level", default=default_level): vol.In(LEVELS),
            }
        )

        return self.async_show_form(
            step_id="level",
            data_schema=schema,
            description_placeholders={
                "language": lang_name,
                "code": lang_code.upper(),
                "index": str(self._current_lang_index + 1),
                "total": str(len(self._selected_languages)),
                "recommended": "A1" if lang_code in RECOMMEND_A1 else "A2",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> Quiz8LanguagesOptionsFlow:
        """Return options flow."""
        return Quiz8LanguagesOptionsFlow(config_entry)


class Quiz8LanguagesOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow (reconfiguration) for Quiz8 Languages."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._selected_languages: list[str] = list(
            config_entry.data.get(CONF_SELECTED_LANGUAGES, [])
        )
        self._language_levels: dict[str, str] = dict(
            config_entry.data.get(CONF_LANGUAGE_LEVELS, {})
        )
        self._current_lang_index: int = 0

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Re-select the 8 languages."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_LANGUAGES, [])
            if len(selected) != MAX_LANGUAGES_SELECTED:
                errors["base"] = "select_exactly_8"
            else:
                self._selected_languages = selected
                # Reset levels for newly selected languages
                self._language_levels = {
                    lang: self._language_levels.get(lang, "A1")
                    for lang in selected
                }
                self._current_lang_index = 0
                return await self.async_step_level()

        lang_options = {
            code: f"{name} ({code.upper()})"
            for code, name in SUPPORTED_LANGUAGES.items()
        }

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SELECTED_LANGUAGES,
                    default=self._selected_languages,
                ): vol.All(
                    cv.multi_select(lang_options),
                    vol.Length(min=MAX_LANGUAGES_SELECTED, max=MAX_LANGUAGES_SELECTED),
                )
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "count": str(MAX_LANGUAGES_SELECTED),
            },
        )

    async def async_step_level(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set level for each language."""
        if user_input is not None:
            lang_code = self._selected_languages[self._current_lang_index]
            self._language_levels[lang_code] = user_input["level"]
            self._current_lang_index += 1

        if self._current_lang_index >= len(self._selected_languages):
            # Save updated config
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={
                    CONF_SELECTED_LANGUAGES: self._selected_languages,
                    CONF_LANGUAGE_LEVELS: self._language_levels,
                },
            )
            return self.async_create_entry(title="", data={})

        lang_code = self._selected_languages[self._current_lang_index]
        lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)
        current_level = self._language_levels.get(lang_code, "A1")

        schema = vol.Schema(
            {
                vol.Required("level", default=current_level): vol.In(LEVELS),
            }
        )

        return self.async_show_form(
            step_id="level",
            data_schema=schema,
            description_placeholders={
                "language": lang_name,
                "code": lang_code.upper(),
                "index": str(self._current_lang_index + 1),
                "total": str(len(self._selected_languages)),
                "recommended": "A1" if lang_code in RECOMMEND_A1 else "A2",
            },
        )