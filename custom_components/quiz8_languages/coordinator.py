"""Coordinator for quiz8_languages integration."""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import random
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LANGUAGE_LEVELS,
    CONF_SELECTED_LANGUAGES,
    DOMAIN,
    FALLBACK_UI_LANGUAGE,
    MASTERY_THRESHOLD,
    NON_LATIN_SCRIPTS,
    STORAGE_KEY_PROGRESS,
    STORAGE_VERSION,
    SUPPORTED_UI_LANGUAGES,
    UPDATE_INTERVAL,
    WORDS_PER_SESSION,
    WORDS_PER_ROUND,
)

_LOGGER = logging.getLogger(__name__)

VOCAB_DIR = pathlib.Path(__file__).parent / "vocabulary"
ROUNDS_PER_LANGUAGE = 3  # 3 rondas × 8 palabras = 24 por idioma


class Quiz8LanguagesCoordinator(DataUpdateCoordinator):
    """Coordinator managing vocabulary, progress, and game state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.entry = entry
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY_PROGRESS)
        self._loaded_vocab: dict[str, dict[str, Any]] = {}
        self._progress: dict[str, Any] = {}
        self._session: dict[str, Any] = {}
        self._ui_language: str = FALLBACK_UI_LANGUAGE
        self._daily_pool: dict[str, list[str]] = {}
        self._pool_date: date | None = None

    # ------------------------------------------------------------------ #
    #  Properties                                                          #
    # ------------------------------------------------------------------ #

    @property
    def selected_languages(self) -> list[str]:
        return self.entry.data.get(CONF_SELECTED_LANGUAGES, [])

    @property
    def language_levels(self) -> dict[str, str]:
        return self.entry.data.get(CONF_LANGUAGE_LEVELS, {})

    @property
    def ui_language(self) -> str:
        return self._ui_language

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    async def async_setup(self) -> None:
        await self._async_load_progress()
        await self._async_load_active_vocabularies()
        self._refresh_ui_language()
        self._ensure_daily_pool()
        self._ensure_session()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            self._refresh_ui_language()
            self._ensure_daily_pool()
            self._ensure_session()
            return self._build_state()
        except Exception as err:
            raise UpdateFailed(f"Quiz8 Languages update error: {err}") from err

    # ------------------------------------------------------------------ #
    #  Vocabulary loading                                                  #
    # ------------------------------------------------------------------ #

    async def _async_load_active_vocabularies(self) -> None:
        tasks = [
            self._async_load_language_vocab(lang, self.language_levels.get(lang, "A1"))
            for lang in self.selected_languages
        ]
        await asyncio.gather(*tasks)

    async def _async_load_language_vocab(self, lang: str, level: str) -> None:
        if lang in self._loaded_vocab:
            return
        file_path = VOCAB_DIR / lang / f"{level}.json"
        if not file_path.exists():
            _LOGGER.warning("Vocabulary file not found: %s", file_path)
            self._loaded_vocab[lang] = {}
            return
        try:
            data = await self.hass.async_add_executor_job(self._read_json, file_path)
            self._loaded_vocab[lang] = {w["id"]: w for w in data.get("words", [])}
            _LOGGER.debug("Loaded %d words for %s/%s", len(self._loaded_vocab[lang]), lang, level)
        except Exception as err:
            _LOGGER.error("Error loading vocabulary for %s/%s: %s", lang, level, err)
            self._loaded_vocab[lang] = {}

    async def async_reload_language(self, lang: str, new_level: str) -> None:
        self._loaded_vocab.pop(lang, None)
        self._daily_pool.pop(lang, None)
        await self._async_load_language_vocab(lang, new_level)
        self._ensure_daily_pool()
        await self.async_refresh()

    @staticmethod
    def _read_json(file_path: pathlib.Path) -> dict:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------ #
    #  Daily pool                                                          #
    # ------------------------------------------------------------------ #

    def _ensure_daily_pool(self) -> None:
        today = dt_util.now().date()
        if self._pool_date == today:
            return
        self._pool_date = today
        self._daily_pool = {}

        for lang in self.selected_languages:
            vocab = self._loaded_vocab.get(lang, {})
            if not vocab:
                continue
            word_ids = list(vocab.keys())
            lang_progress = self._progress.get("mastery", {}).get(lang, {})
            non_mastered = [w for w in word_ids if lang_progress.get(w, 0) < MASTERY_THRESHOLD]
            mastered     = [w for w in word_ids if lang_progress.get(w, 0) >= MASTERY_THRESHOLD]

            pool: list[str] = []
            if len(non_mastered) >= WORDS_PER_SESSION:
                pool = random.sample(non_mastered, WORDS_PER_SESSION)
            else:
                pool = non_mastered[:]
                remaining = WORDS_PER_SESSION - len(pool)
                if mastered and remaining > 0:
                    pool += random.sample(mastered, min(remaining, len(mastered)))
            random.shuffle(pool)
            self._daily_pool[lang] = pool

    # ------------------------------------------------------------------ #
    #  Session                                                             #
    # ------------------------------------------------------------------ #

    def _ensure_session(self) -> None:
        today = str(dt_util.now().date())
        if self._session.get("date") == today:
            return
        self._session = {
            "date": today,
            "active_language": self.selected_languages[0] if self.selected_languages else None,
            "score": 0,
            "rounds_completed": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
            "languages": {
                lang: {"pool_index": 0, "rounds_done": 0, "score": 0}
                for lang in self.selected_languages
            },
        }

    # ------------------------------------------------------------------ #
    #  Game API                                                            #
    # ------------------------------------------------------------------ #

    def get_language_rounds(self, lang: str) -> dict[str, Any] | None:
        """Return 3 rounds of 8 words (24 total) for a language.

        This is the primary data source for the Lovelace card.
        All 24 words are returned at once so the card can play
        all 3 rounds without any further backend calls.
        """
        vocab = self._loaded_vocab.get(lang, {})
        pool  = self._daily_pool.get(lang, [])
        lang_session = self._session.get("languages", {}).get(lang, {})
        idx = lang_session.get("pool_index", 0)

        words_needed = WORDS_PER_ROUND * ROUNDS_PER_LANGUAGE  # 24

        if not pool or idx >= len(pool):
            return None

        # Take up to 24 words from current position
        round_ids = pool[idx: idx + words_needed]
        if not round_ids:
            return None

        # Build word objects
        words = []
        for wid in round_ids:
            word_data = vocab.get(wid)
            if not word_data:
                continue
            words.append({
                "id":              wid,
                "word":            word_data.get("word", ""),
                "transliteration": word_data.get("transliteration"),
                "translation":     self._get_translation(word_data),
                "mastery":         self._get_mastery(lang, wid),
            })

        if not words:
            return None

        # Split into 3 rounds of WORDS_PER_ROUND each
        rounds = []
        for r in range(ROUNDS_PER_LANGUAGE):
            start = r * WORDS_PER_ROUND
            end   = start + WORDS_PER_ROUND
            round_words = words[start:end]
            if not round_words:
                break

            translations = [w["translation"] for w in round_words]
            shuffled     = translations[:]
            random.shuffle(shuffled)

            rounds.append({
                "round_number":       r + 1,
                "words_left":         [{"id": w["id"], "word": w["word"], "transliteration": w.get("transliteration")} for w in round_words],
                "translations_right": shuffled,
                "word_to_translation": {w["id"]: w["translation"] for w in round_words},
            })

        return {
            "language":    lang,
            "rounds":      rounds,
            "ui_language": self._ui_language,
            "pool_progress": f"{idx}/{len(pool)}",
        }

    def register_answer(self, lang: str, word_id: str, correct: bool) -> dict[str, Any]:
        lang_progress = self._progress.setdefault("mastery", {}).setdefault(lang, {})
        current = lang_progress.get(word_id, 0)

        if correct:
            new_mastery = min(current + 1, MASTERY_THRESHOLD)
            self._session["correct_answers"] = self._session.get("correct_answers", 0) + 1
            self._session["score"] = self._session.get("score", 0) + self._score_for_mastery(current)
            lang_session = self._session.setdefault("languages", {}).setdefault(lang, {})
            lang_session["score"] = lang_session.get("score", 0) + self._score_for_mastery(current)
        else:
            new_mastery = max(0, current - 1)
            self._session["wrong_answers"] = self._session.get("wrong_answers", 0) + 1

        lang_progress[word_id] = new_mastery
        just_mastered = current < MASTERY_THRESHOLD and new_mastery >= MASTERY_THRESHOLD
        if just_mastered:
            self.hass.bus.async_fire("quiz8_languages_word_mastered", {"language": lang, "word_id": word_id})

        return {"word_id": word_id, "correct": correct, "mastery": new_mastery, "just_mastered": just_mastered}

    def complete_round(self, lang: str) -> dict[str, Any]:
        """Advance pool_index by WORDS_PER_ROUND after each round."""
        lang_session = self._session.setdefault("languages", {}).setdefault(lang, {})
        lang_session["rounds_done"]  = lang_session.get("rounds_done", 0) + 1
        lang_session["pool_index"]   = lang_session.get("pool_index", 0) + WORDS_PER_ROUND
        self._session["rounds_completed"] = self._session.get("rounds_completed", 0) + 1

        pool          = self._daily_pool.get(lang, [])
        pool_index    = lang_session["pool_index"]
        session_complete = pool_index >= len(pool)

        if session_complete:
            self.hass.bus.async_fire("quiz8_languages_session_complete",
                {"language": lang, "score": lang_session.get("score", 0)})

        self.hass.bus.async_fire("quiz8_languages_round_complete",
            {"language": lang, "round": lang_session["rounds_done"], "score": lang_session.get("score", 0)})

        self.hass.async_create_task(self._async_save_progress())
        return {"rounds_done": lang_session["rounds_done"], "pool_index": pool_index,
                "total_pool": len(pool), "session_complete": session_complete}

    def set_active_language(self, lang: str) -> None:
        if lang in self.selected_languages:
            self._session["active_language"] = lang

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def get_words_mastered(self, lang: str | None = None) -> int:
        mastery = self._progress.get("mastery", {})
        if lang:
            return sum(1 for v in mastery.get(lang, {}).values() if v >= MASTERY_THRESHOLD)
        return sum(1 for ld in mastery.values() for v in ld.values() if v >= MASTERY_THRESHOLD)

    def get_accuracy(self) -> float:
        correct = self._session.get("correct_answers", 0)
        wrong   = self._session.get("wrong_answers", 0)
        total   = correct + wrong
        return round((correct / total) * 100, 1) if total > 0 else 0.0

    def get_daily_streak(self) -> int:
        return self._progress.get("streak", {}).get("current", 0)

    def _get_translation(self, word_data: dict) -> str:
        translations = word_data.get("translations", {})
        return (translations.get(self._ui_language)
                or translations.get(FALLBACK_UI_LANGUAGE)
                or next(iter(translations.values()), "?"))

    def _get_mastery(self, lang: str, word_id: str) -> int:
        return self._progress.get("mastery", {}).get(lang, {}).get(word_id, 0)

    @staticmethod
    def _score_for_mastery(current_mastery: int) -> int:
        return max(1, MASTERY_THRESHOLD - current_mastery)

    def _refresh_ui_language(self) -> None:
        ha_lang = getattr(self.hass.config, "language", FALLBACK_UI_LANGUAGE)
        self._ui_language = ha_lang if ha_lang in SUPPORTED_UI_LANGUAGES else FALLBACK_UI_LANGUAGE

    def _build_state(self) -> dict[str, Any]:
        return {
            "score":                 self._session.get("score", 0),
            "rounds_completed":      self._session.get("rounds_completed", 0),
            "correct_answers":       self._session.get("correct_answers", 0),
            "wrong_answers":         self._session.get("wrong_answers", 0),
            "accuracy":              self.get_accuracy(),
            "streak":                self.get_daily_streak(),
            "words_mastered_total":  self.get_words_mastered(),
            "words_mastered_per_lang": {lang: self.get_words_mastered(lang) for lang in self.selected_languages},
            "active_language":       self._session.get("active_language"),
            "ui_language":           self._ui_language,
            "session_date":          self._session.get("date"),
            "languages":             self._session.get("languages", {}),
        }

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    async def _async_load_progress(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self._progress = stored
            self._update_streak()
        else:
            self._progress = {"mastery": {}, "streak": {"current": 0, "last_date": None}}

    async def _async_save_progress(self) -> None:
        try:
            await self._store.async_save(self._progress)
        except Exception as err:
            _LOGGER.error("Failed to save progress: %s", err)

    def _update_streak(self) -> None:
        streak = self._progress.setdefault("streak", {"current": 0, "last_date": None})
        today  = str(dt_util.now().date())
        last   = streak.get("last_date")
        if last is None:
            streak["current"] = 1; streak["last_date"] = today
        elif last == today:
            pass
        else:
            try:
                diff = (dt_util.now().date() - date.fromisoformat(last)).days
                streak["current"] = streak["current"] + 1 if diff == 1 else 1
                streak["last_date"] = today
            except ValueError:
                streak["current"] = 1; streak["last_date"] = today

    async def async_mark_day_played(self) -> None:
        self._update_streak()
        await self._async_save_progress()
        