# Quick Start Guide - SLD Intelligence System

## ⚡ Option 1: LLava + Ollama (RECOMMENDED - Fastest Setup)

**Why LLava?** ✅ Free | ✅ Unlimited | ✅ Offline | ✅ No API Key Needed

### Installation (5 minutes)

**Step 1**: Install Ollama
- **Windows**: Download from https://ollama.ai/download/windows → Run installer
- **Mac**: `brew install ollama`
- **Linux**: `curl https://ollama.ai/install.sh | sh`

**Step 2**: Pull LLava model (first time only)
```bash
ollama pull llava
```

**Step 3**: Run extraction
```bash
cd "e:\PROJECTS\Smart Electrical SLD Intelligence"
python scripts/extract_llava.py data/real/katra.jpg
```

✅ Done! No keys, no costs, works offline.

---

## ☁️ Option 2: Gemini API (Higher Accuracy, Cloud-Based)

**Why Gemini?** ✅ Faster | ✅ Higher accuracy | ❌ Quota limited (20/day free)

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

## 🔄 Batch Processing (Extract All SLDs)

```bash
# With LLava (recommended - no limits)
python scripts/batch_process.py data/real/ llava results/

# With Gemini (if you have quota)
python scripts/batch_process.py data/real/ gemini results/
```

---

## 📊 Compare Models

```bash
python scripts/compare_models.py data/real/katra.jpg
```

Shows: Speed, accuracy, cost comparison for LLava vs Gemini

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
| `403 Unauthorized` (Gemini) | Check GEMINI_API_KEY in .env file |
| Out of memory | Switch to Gemini (cloud-based, no memory needed) |

---

## 📚 Next Steps

1. **Extract real SLD**: `python scripts/extract_llava.py data/real/katra.jpg`
2. **Batch extract**: `python scripts/batch_process.py data/real/ llava`
3. **Compare accuracy**: `python scripts/compare_models.py data/real/katra.jpg`
4. **Check results**: `cat data/real/katra_output.json`

**See [METHODOLOGY.md](METHODOLOGY.md) for technical details.**
