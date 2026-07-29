# ● Pico — Offline Wake-Word Voice Assistant

Pico is a lightweight, local-first voice assistant for your desktop. It listens continuously for a wake word ("Hey Pico"), records your question, transcribes it, sends it to an LLM for a short spoken-style answer, and speaks the response back to you — all with sub-second-feeling latency thanks to Groq's inference speed.

```
🎤 "Hey Pico"  →  ● chime  →  🎙️ record  →  📝 Whisper STT  →  🧠 LLM  →  🔊 TTS reply
```

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Clone the repo](#1-clone-the-repo)
  - [2. Create a virtual environment](#2-create-a-virtual-environment)
  - [3. Install system dependencies](#3-install-system-dependencies)
  - [4. Install Python dependencies](#4-install-python-dependencies)
  - [5. Download the Vosk wake-word model](#5-download-the-vosk-wake-word-model)
  - [6. Configure API keys](#6-configure-api-keys)
- [Usage](#usage)
- [Configuration Reference](#configuration-reference)
- [Customizing Pico](#customizing-pico)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Roadmap Ideas](#roadmap-ideas)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Features

- **Always-on wake word detection** using [Vosk](https://alphacephei.com/vosk/) — runs fully offline, no cloud call until you actually speak to it.
- **Ultra-fast speech-to-text** via Groq's hosted `whisper-large-v3-turbo`.
- **Fast LLM reasoning** via Groq's hosted `llama-3.3-70b-versatile`, prompted to give short, speakable answers.
- **Natural-sounding text-to-speech** via Microsoft [edge-tts](https://github.com/rany2/edge-tts) (free, no API key required).
- **Clean audio feedback** — a synthesized two-tone chime (no external sound files) plays when the wake word is detected.
- **Simple, single-file architecture** — easy to read, easy to hack on.

---

## How It Works

1. **`sounddevice.RawInputStream`** streams raw microphone audio in small chunks into a queue.
2. **Vosk's `KaldiRecognizer`**, restricted to a small grammar (`"hey pico"`, `"hello pico"`, `[unk]`), continuously scans that audio for the wake phrase. Because the grammar is constrained, this runs efficiently even on modest hardware.
3. Once the wake word is detected:
   - A short synthesized chime plays (generated with `numpy`, played with `pygame`) to confirm Pico is listening.
   - The next ~4 seconds of audio are recorded via `sounddevice.rec`.
   - That audio is sent to **Groq's Whisper API** for transcription.
   - The transcribed text is sent to **Groq's Llama 3.3 70B** with a system prompt that asks for a 1–2 sentence, speech-friendly answer.
   - The answer is converted to speech with **edge-tts** and played back through `pygame.mixer`.
4. The loop resets and goes back to listening for the wake word.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python | 3.9 – 3.12 recommended |
| Microphone | Any system input device |
| Speakers/headphones | For chime + TTS playback |
| Groq API key | Free tier available — [console.groq.com](https://console.groq.com) |
| Internet connection | Needed for Whisper STT, LLM, and edge-tts (wake word detection itself is offline) |

**OS support:** Works on Windows, macOS, and Linux. Audio I/O libraries (`sounddevice`, `pygame`) occasionally need extra OS-level setup — see [Troubleshooting](#troubleshooting).

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/pico-assistant.git
cd pico-assistant
```

### 2. Create a virtual environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install system dependencies

`sounddevice` relies on **PortAudio**, and `pygame`'s mixer relies on **SDL2**. Python wheels usually bundle these, but if you hit import/audio errors, install them manually:

**macOS (Homebrew):**
```bash
brew install portaudio
```

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install portaudio19-dev python3-dev libsdl2-mixer-2.0-0 ffmpeg
```

**Windows:**
No extra system packages are typically needed — the `sounddevice` and `pygame` wheels ship with PortAudio/SDL2 binaries.

> `ffmpeg` is recommended on all platforms since `edge-tts` output plays more reliably when it's available.

### 4. Install Python dependencies

Create a `requirements.txt` with the following contents:

```txt
groq
edge-tts
vosk
sounddevice
soundfile
pygame
numpy
python-dotenv
```

Then install:

```bash
pip install -r requirements.txt
```

### 5. Download the Vosk wake-word model

The script loads a model with `vosk.Model(lang="en-us")`. On first run, Vosk will attempt to auto-download a small English model. If that fails (or you want to pick the model explicitly), download one manually from the [Vosk model list](https://alphacephei.com/vosk/models) and unzip it into your project directory, e.g.:

```bash
# Example: small, fast English model
curl -LO https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

Then point the code at it explicitly if needed:

```python
model = vosk.Model(model_path="vosk-model-small-en-us-0.15")
```

### 6. Configure API keys

**Never commit real API keys to the repo.** Instead:

1. Create a file named `.env` in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

2. Add `.env` to your `.gitignore`:

```gitignore
.env
venv/
__pycache__/
*.mp3
```

3. Update the top of `pico.py` to load the key from the environment instead of hardcoding it:

```python
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
groq_client = Groq(api_key=GROQ_API_KEY)
```

Get a free Groq API key at **[console.groq.com/keys](https://console.groq.com/keys)**.

---

## Usage

Activate your virtual environment, then run:

```bash
python pico.py
```

You should see:

```
● Loading Vosk wake word engine...
--------------------------------------------------
● PICO ASSISTANT READY
  Say 'Hey Pico' into your microphone.
--------------------------------------------------
```

Say **"Hey Pico"** or **"Hello Pico"**. You'll hear a short chime, then you have ~4 seconds to ask your question out loud. Pico will transcribe it, think, and reply.

Press `Ctrl+C` to exit at any time.

---

## Configuration Reference

All of the following are defined near the top of `pico.py`:

| Variable | Default | Description |
|---|---|---|
| `TTS_VOICE` | `"en-US-AvaNeural"` | Any [edge-tts voice name](https://github.com/rany2/edge-tts#voice-list) — run `edge-tts --list-voices` to see all options |
| `SAMPLE_RATE` | `16000` | Sample rate used for wake-word detection and STT recording (Vosk expects 16kHz) |
| Wake phrases | `"hey pico"`, `"hello pico"` | Defined in the Vosk `grammar` string inside `main()` |
| Recording duration | `4.0` seconds | Passed to `record_question(duration=...)` |
| LLM model | `llama-3.3-70b-versatile` | Groq-hosted model used for reasoning |
| STT model | `whisper-large-v3-turbo` | Groq-hosted Whisper variant |
| `max_tokens` | `100` | Caps LLM response length to keep replies short and speakable |
| `temperature` | `0.6` | LLM sampling temperature |

---

## Customizing Pico

- **Change the wake word:** edit the `grammar` string and the `if "hey pico" in text or ...` check in `main()`.
- **Change the voice:** set `TTS_VOICE` to any voice from `edge-tts --list-voices` (e.g. `"en-GB-RyanNeural"`, `"en-US-GuyNeural"`).
- **Longer/shorter answers:** adjust `max_tokens` and the system prompt in `query_llm()`.
- **Longer recording window:** increase the `duration` passed to `record_question()` if you tend to ask longer questions.
- **Swap the LLM provider:** the `API_KEYS` dict already anticipates OpenRouter, ModelScope, NVIDIA NIM, and Gemini. `query_llm()` currently only wires up Groq — extend it with an `if provider == "OPENROUTER": ...` branch calling that provider's chat completions endpoint.

---

## Project Structure

```
pico-assistant/
├── pico.py              # Main application (wake word → STT → LLM → TTS loop)
├── requirements.txt     # Python dependencies
├── .env.example         # Template for required environment variables
├── .gitignore
└── README.md
```

Create a `.env.example` (safe to commit, contains no real secrets) so contributors know what to fill in:

```env
GROQ_API_KEY=
```

---

## Troubleshooting

**`OSError: PortAudio library not found`**
Install PortAudio for your OS (see [Installation → System dependencies](#3-install-system-dependencies)), then reinstall `sounddevice`.

**No sound / `pygame.error: No available audio device`**
Some Linux environments (headless servers, WSL) have no audio backend. Ensure `pulseaudio` or `alsa` is running, or test on a machine with a real audio device.

**Vosk model fails to download automatically**
Download a model manually from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) and load it with `vosk.Model(model_path="...")` instead of `vosk.Model(lang="en-us")`.

**Wake word not triggering**
- Speak clearly and check your mic input level in your OS sound settings.
- Try the larger Vosk model (`vosk-model-en-us-0.22`) instead of the small one — it's slower to load but more accurate.
- Confirm the correct input device is selected; you can list devices with:
  ```python
  import sounddevice as sd
  print(sd.query_devices())
  ```

**`groq.AuthenticationError` / 401 errors**
Your `GROQ_API_KEY` is missing, invalid, or not loaded. Confirm `.env` exists, contains the right key, and that `load_dotenv()` runs before the `Groq()` client is created.

**Choppy or cut-off TTS playback**
Ensure `ffmpeg` is installed and on your `PATH` — `edge-tts` and `pygame` both benefit from it for reliable MP3 decoding.

---

## Security Notes

- **Never commit API keys.** Use `.env` + `.gitignore` as shown above. Consider adding a pre-commit hook or a tool like [gitleaks](https://github.com/gitleaks/gitleaks) to catch accidental key commits.
- **Rotate any key that has ever been hardcoded in source, chat logs, or screenshots** — treat exposure as compromise even if the repo was private.
- If you plan to distribute a packaged/compiled version of this app to end users, don't embed your own key in the binary; require each user to supply their own.

---

## Roadmap Ideas

- [ ] Multi-turn conversation memory (currently each question is stateless)
- [ ] Streaming TTS playback to reduce perceived latency
- [ ] Support for additional LLM providers (OpenRouter, NVIDIA NIM, Gemini) with automatic fallback
- [ ] Configurable wake-word sensitivity / custom wake phrases via CLI flag
- [ ] Push-to-talk mode as an alternative to wake-word listening
- [ ] Dockerfile for easier cross-platform setup

---

## Contributing

Contributions are welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-idea`)
3. Commit your changes
4. Open a pull request describing what you changed and why

Please don't include personal API keys, audio recordings, or other private data in PRs.

---

## License

Released under the [MIT License](LICENSE) — free to use, modify, and distribute, with attribution appreciated.

---

## Acknowledgments

- [Vosk](https://alphacephei.com/vosk/) — offline speech recognition toolkit
- [Groq](https://groq.com) — high-speed LLM and Whisper inference
- [edge-tts](https://github.com/rany2/edge-tts) — free access to Microsoft Edge's neural TTS voices
- [Pygame](https://www.pygame.org) — audio playback engine
- [sounddevice](https://python-sounddevice.readthedocs.io) — Python bindings for PortAudio

---

*Made with ● — say "Hey Pico" and start talking.*
