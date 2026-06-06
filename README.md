
<div align="center">

# Quiz8 Languages — Home Assistant Integration

<img src="https://github.com/janfajessen/Quiz8-Languages---Home-Assistant/blob/c52439777b326e7db3e634f40903392aa059f3ba/custom_components/quiz8_languages/brand/icon%402x.png" width="25%"/>

![Version](https://img.shields.io/badge/version-1.5.28-blue?style=for-the-badge)
![HA](https://img.shields.io/badge/Home%20Assistant-2024.1+-orange?style=for-the-badge&logo=home-assistant)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python)
![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow?style=for-the-badge&logo=buymeacoffee)](https://www.buymeacoffee.com/janfajessen)
[![Patreon](https://img.shields.io/badge/Patreon-Support-red?style=for-the-badge&logo=patreon)](https://www.patreon.com/janfajessen)
<!--[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support-teal?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/janfajessen)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-Support-pink?style=for-the-badge&logo=githubsponsors)](https://github.com/sponsors/janfajessen)


[![PayPal](https://img.shields.io/badge/PayPal-Donate-blue?style=for-the-badge&logo=paypal)](https://paypal.me/janfajessen)-->

A Home Assistant custom integration that turns your smart home into a language learning platform. Practice vocabulary across up to 8 languages simultaneously, with spaced repetition, daily streaks, and mastery tracking — all from your Lovelace dashboard.


</div>

---

## Features

- **8 languages at once** — select exactly 8 from 28 supported languages
- **CEFR levels** — A1, A2, B1, B2, C1 per language (vocabulary files sold separately or self-made)
- **Spaced repetition** — words you struggle with appear more often; mastered words are gradually retired
- **Daily pool** — 100 words sampled per language per day, refreshed at midnight
- **3 rounds × 8 pairs** — 24 word pairs per language per session
- **Mastery tracking** — a word needs 10 correct answers to be considered mastered
- **Daily streak** — keeps track of consecutive days played
- **Session accuracy** — correct vs wrong answers per session
- **HA services** — register answers, complete rounds, switch active language, mark day played
- **Fully local** — no API keys, no cloud, no internet required

---

## Supported Languages

| Code | Language | Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|------|----------|
| `de` | German | `nl` | Dutch | `ru` | Russian | `hi` | Hindi |
| `fr` | French | `sv` | Swedish | `pl` | Polish | `ja` | Japanese |
| `en` | English | `no` | Norwegian | `cs` | Czech | `ko` | Korean |
| `it` | Italian | `da` | Danish | `ro` | Romanian | `zh` | Chinese |
| `pt` | Portuguese | `fi` | Finnish | `hu` | Hungarian | `he` | Hebrew |
| `el` | Greek | `tr` | Turkish | `uk` | Ukrainian | `ar` | Arabic |
| `es` | Spanish | `ca` | Catalan | `eu` | Basque | `gl` | Galician |


Languages with non-Latin scripts (`ru`, `el`, `uk`, `ar`, `zh`, `ja`, `ko`, `hi`, `he`) support optional transliteration fields in vocabulary files.

---

## Requirements

- Home Assistant 2024.1 or later
- Vocabulary JSON files (one per language/level combination)

---

## Installation

### Manual

1. Copy the `quiz8_languages` folder into your `/config/custom_components/` directory:

```
/config/custom_components/quiz8_languages/
    __init__.py
    coordinator.py
    sensor.py
    config_flow.py
    const.py
    manifest.json
    services.yaml
    strings.json
    vocabulary/
        de/
            A1.json
            B1.json
        fr/
            A1.json
        ...
```

2. Restart Home Assistant.

3. Go to **Settings → Integrations → Add Integration** and search for **Quiz8 Languages**.

<img src="https://github.com/janfajessen/Quiz8-Languages---Home-Assistant/blob/c52439777b326e7db3e634f40903392aa059f3ba/custom_components/quiz8_languages/brand/icon%402x.png" width="100"/>


### HACS (coming soon)

Add the repository `https://github.com/janfajessen/Quiz8-Languages---Home-Assistant` as a custom repository in HACS (category: Integration).

---

## Vocabulary File Format

Each vocabulary file lives at `vocabulary/{lang_code}/{level}.json` and follows this structure:

```json
{
  "language": "de",
  "level": "A1",
  "words": [
    {
      "id": "de_A1_001",
      "word": "Haus",
      "transliteration": null,
      "translations": {
        "es": "casa",
        "en": "house",
        "fr": "maison"
      },
      "category": "home"
    }
  ]
}
```

The `translations` object should include your Home Assistant UI language plus any others you want as fallback. The integration picks the translation matching `hass.config.language` automatically, falling back to English if not found.

For non-Latin script languages, `transliteration` can be a string (e.g. romanization) displayed below the word in the card.

---

## Configuration

During setup you will go through two steps:

**Step 1 — Select exactly 8 languages** from the 28 available.

**Step 2 — Set a CEFR level for each language** (A1 recommended for complex scripts or grammar systems such as Japanese, Arabic, Hungarian or Finnish).

You can reconfigure at any time via **Settings → Integrations → Quiz8 Languages → Configure**.

---

## Sensors

After setup the following sensors are created:

| Entity | Description |
|--------|-------------|
| `sensor.quiz8_languages_session_score` | Total session score in points |
| `sensor.quiz8_languages_daily_streak` | Consecutive days played |
| `sensor.quiz8_languages_words_mastered` | Total words mastered across all languages |
| `sensor.quiz8_languages_session_accuracy` | Correct answer percentage for today |
| `sensor.quiz8_languages_rounds_completed` | Total rounds completed today |
| `sensor.quiz8_languages_active_language` | Currently active learning language |
| `sensor.quiz8_languages_session_progress` | Words seen today across all languages |
| `sensor.quiz8_languages_language_rounds` | **Main card sensor** — exposes 24 word pairs (3 rounds × 8) for the active language |
| `sensor.quiz8_languages_{language}_progress` | Per-language progress (one per selected language) |

The `language_rounds` sensor is the data source for the companion Lovelace card. Its attributes contain the full round data (words, shuffled translations, word-to-translation map) ready to consume.

---

## Services

| Service | Description |
|---------|-------------|
| `quiz8_languages.register_answer` | Register a correct or incorrect answer for a word |
| `quiz8_languages.complete_round` | Advance pool index after completing a round |
| `quiz8_languages.set_active_language` | Switch the active language (triggers sensor update) |
| `quiz8_languages.mark_day_played` | Mark today as played and update the daily streak |

---

## How Scoring Works

- Each correct answer scores between 1 and 10 points depending on the word's current mastery level
- Lower mastery = more points (harder words are more rewarding)
- Wrong answers reduce mastery by 1 (minimum 0)
- Correct answers increase mastery by 1 (maximum 10 = mastered)
- Mastered words are still included occasionally in the daily pool for review

---

## Links

- **Lovelace card:** [Quiz8 Languages Lovelace Card](https://github.com/janfajessen/Quiz8-Languages-lovelace-card---Home-Assistant)
- **Issues:** [GitHub Issues](https://github.com/janfajessen/Quiz8-Languages---Home-Assistant/issues)

---


---


*If this integration or card is useful to you, consider giving it a ⭐ on GitHub.*
Or consider supporting development!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow?style=for-the-badge&logo=buymeacoffee)
](https://www.buymeacoffee.com/janfajessen) 
[![Patreon](https://img.shields.io/badge/Patreon-Support-red?style=for-the-badge&logo=patreon)](https://www.patreon.com/janfajessen)
</div>


## License


MIT License — see [LICENSE](LICENSE) for details.


© [@janfajessen](https://github.com/janfajessen)
