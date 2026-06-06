"""Constants for quiz8_languages integration."""

DOMAIN = "quiz8_languages"
PLATFORMS = ["sensor"]

# Coordinator update interval (seconds) - daily refresh of word pool
UPDATE_INTERVAL = 3600  # 1 hour, but daily pool only changes at midnight

# Vocabulary settings
WORDS_PER_SESSION = 100       # Words sampled per day per language
WORDS_PER_ROUND = 8           # Cards shown per round (left + right columns) ← CAMBIADO a 8
MASTERY_THRESHOLD = 10        # Times correct to consider a word "mastered"
MAX_LANGUAGES_SELECTED = 8    # Always exactly 8 languages
VOCAB_PER_LEVEL = 500         # Words per language per level file

# CEFR Levels
LEVELS = ["A1", "A2", "B1", "B2", "C1"]

# Supported learning languages (origin column) - 28 languages
SUPPORTED_LANGUAGES = {
    # Western Europe
    "de": "German",
    "fr": "French",
    "en": "English",
    "it": "Italian",
    "pt": "Portuguese",
    "es": "Spanish",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    # Eastern Europe
    "ru": "Russian",
    "pl": "Polish",
    "cs": "Czech",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "uk": "Ukrainian",
    "tr": "Turkish",
    # Iberian Peninsula
    "ca": "Catalan",
    "eu": "Basque",
    "gl": "Galician",
    # Asian / Other
    "ar": "Arabic",
    "zh": "Chinese (Mandarin)",
    "ja": "Japanese",
    "ko": "Korean",
    "hi": "Hindi",
    "he": "Hebrew",
}

# Languages that use non-latin scripts (need transliteration)
NON_LATIN_SCRIPTS = {"ru", "el", "uk", "ar", "zh", "ja", "ko", "hi", "he"}

# Languages recommended to start at A1 (complex scripts or grammar)
RECOMMEND_A1 = {"ru", "el", "uk", "ar", "zh", "ja", "ko", "hi", "he", "fi", "hu", "eu"}

# Supported UI languages for the translation column (right side)
# These match hass.config.language values
SUPPORTED_UI_LANGUAGES = {
    "es", "en", "fr", "de", "it", "pt", "ru", "pl", "ca",
    "nl", "sv", "no", "da", "fi", "cs", "ro", "hu", "el",
    "uk", "tr", "eu", "gl", "ar", "zh", "ja", "ko", "hi", "he",
}

# Fallback UI language if hass.config.language not in supported list
FALLBACK_UI_LANGUAGE = "en"

# Config entry keys
CONF_SELECTED_LANGUAGES = "selected_languages"
CONF_LANGUAGE_LEVELS = "language_levels"  # dict: {lang_code: level}

# Storage keys
STORAGE_KEY_PROGRESS = f"{DOMAIN}_progress"
STORAGE_VERSION = 1

# Sensor names
SENSOR_SCORE = "score"
SENSOR_ROUNDS_COMPLETED = "rounds_completed"
SENSOR_STREAK = "daily_streak"
SENSOR_WORDS_MASTERED = "words_mastered"
SENSOR_SESSION_ACCURACY = "session_accuracy"
SENSOR_ACTIVE_LANGUAGE = "active_language"

# Event names
EVENT_ROUND_COMPLETE = f"{DOMAIN}_round_complete"
EVENT_WORD_MASTERED = f"{DOMAIN}_word_mastered"
EVENT_SESSION_COMPLETE = f"{DOMAIN}_session_complete"