# Language Models

This project uses two different speech recognition backends depending on the active keyboard layout.

---

## How It Works

| Layout | Engine | Why |
|--------|--------|-----|
| English (`us`) | VOSK | Fast, offline, no delay |
| Arabic (`ara`) | Whisper (faster-whisper) | Far more accurate for Arabic; VOSK Arabic models are too inaccurate |

---

## English: VOSK Models

VOSK models are downloaded and stored in `~/.config/nerd-dictation/`.

### Directory Structure

```
~/.config/nerd-dictation/
└── model/          ← English model (required)
```

### Available English Models

| Model | Size | Quality |
|-------|------|---------|
| `vosk-model-small-en-us-0.15` | 40 MB | Good — recommended for most users |
| `vosk-model-en-us-0.22` | 1.8 GB | Excellent — high accuracy, larger RAM footprint |

### Manual Installation

```bash
cd ~/.config/nerd-dictation
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model
```

Or use the included script:

```bash
./scripts/install-models.sh
```

---

## Arabic: Whisper (faster-whisper)

Arabic dictation uses OpenAI Whisper via the `faster-whisper` Python library. **No model directory is needed** — the model downloads automatically on first use and is cached at:

```
~/.cache/huggingface/hub/
```

### Why Whisper for Arabic?

- VOSK Arabic models have limited training data and poor dialect coverage
- Whisper was trained on 680,000 hours of multilingual audio including Arabic
- Whisper handles Modern Standard Arabic and common dialects
- Accuracy is dramatically better than any available VOSK Arabic model

### Available Whisper Models

| Model | Size | Speed (CPU) | Arabic Quality |
|-------|------|-------------|----------------|
| `tiny` | ~39 MB | Very fast | Low |
| `base` | ~74 MB | Fast | Fair |
| `small` | ~244 MB | Medium | **Good — default** |
| `medium` | ~769 MB | Slow | Better |
| `large-v3` | ~1.5 GB | Very slow | Best |

The default is `small`. To use a larger model, edit `WHISPER_MODEL` in `scripts/dictate-start`:

```bash
# In dictate-start, change:
WHISPER_MODEL="small"
# to:
WHISPER_MODEL="medium"
```

### Pre-downloading the Model

The setup script offers to pre-download the Whisper model. You can also do it manually:

```bash
python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```

This avoids a delay on the first Arabic dictation session.

### First-use Behaviour

The first time Arabic dictation starts, faster-whisper downloads the model (~244 MB for `small`). After that, it loads from the local cache in 2–5 seconds.

You will see **two notifications**:
1. **"Dictation Loading"** — model is being loaded (do not speak yet)
2. **"Dictation Ready"** — recording has started, speak now

---

## Other Languages

Other languages can be added using VOSK models. See [Advanced Options](06-advanced.md#adding-new-languages).

Visit [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) for a full list.

| Language | Code | Model |
|----------|------|-------|
| German | `de` | `vosk-model-de-grpc-0.2` |
| French | `fr` | `vosk-model-fr-0.22` |
| Spanish | `es` | `vosk-model-es-0.42` |
| Russian | `ru` | `vosk-model-ru-0.42` |
| Chinese | `zh` | `vosk-model-cn-0.22` |

---

## Next Steps

- [Configuration](03-configuration.md)
- [Desktop Integration](05-desktop-integration.md)
