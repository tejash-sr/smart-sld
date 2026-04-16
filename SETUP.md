# Quick Start Guide - SLD Intelligence System

## ⚡ DEFAULT: LLava + Ollama (No API Key Needed!)

**Why LLava First?** ✅ Free | ✅ Unlimited | ✅ Offline | ✅ No Setup Required

### Installation (5 minutes)

**Step 1**: Install Ollama
- **Windows**: Download from https://ollama.ai/download/windows → Run installer
- **Mac**: `brew install ollama`
- **Linux**: `curl https://ollama.ai/install.sh | sh`

**Step 2**: Pull LLava model (one-time, ~5GB)
```bash
ollama pull llava
```

**Step 3**: Run extraction immediately!
```bash
python scripts/extract_llava.py data/real/katra.jpg
```

✅ Done! No API keys, no costs, works offline, unlimited processing.

---

## ☁️ OPTIONAL: Gemini API (Faster, Requires API Key)

### Installation (3 minutes)

**Step 1**: Get free API key
1. Visit: https://ai.google.dev/
2. Click "Get API Key" → Create project → Generate key
3. Copy your key

**Step 2**: Configure environment
```bash
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here
```

**Step 3**: Run extraction
```bash
python scripts/extract.py data/real/katra.jpg
```

---

## 🔄 Batch Processing (Recommended - LLava by Default)

```bash
# Extract all SLDs with LLava (default, free, unlimited)
python scripts/batch_process.py data/real/ llava results/

# Or use shorthand (llava is default):
python scripts/batch_process.py data/real/
```

---

## 📊 Model Evaluation (LLava Primary)

```bash
# Evaluate extraction with LLava (always works)
python scripts/compare_models.py data/real/katra.jpg

# Output shows:
# ✅ LLava: Successful extraction
# ⚠️  Gemini: Skipped (if no API key - that's OK!)
# ✅ Recommendation: Use LLava for production
```

---

## ✅ Verify Your Setup

```bash
python preflight_check.py
```

Should show all green ✅

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ollama: command not found` | Restart terminal after installing Ollama |
| `Connection refused` (LLava) | Run `ollama serve` in separate terminal |
| `GEMINI_API_KEY not found` | This is OK! Just use LLava instead (no key needed) |
| `Out of memory` (LLava) | System doesn't have 5GB; use Gemini API instead |
| `Module not found: ollama` | Run `pip install ollama` |

---

## 📚 Next Steps

1. **Extract single SLD**: `python scripts/extract_llava.py data/real/katra.jpg`
2. **Batch extract all**: `python scripts/batch_process.py data/real/`
3. **Evaluate extraction**: `python scripts/compare_models.py data/real/katra.jpg`
4. **View results**: `cat data/real/katra_output.json`

**✅ For FixForward Hackathon: Use LLava (no API key, fully reproducible)**

See [METHODOLOGY.md](METHODOLOGY.md) for technical details.
