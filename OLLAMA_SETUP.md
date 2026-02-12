# Quick Setup Guide for Ollama Benchmark

## The Error You Encountered

The error was caused by a **Pydantic version conflict**:
- Modern LiteLLM requires Pydantic v2.x
- Your environment likely has Pydantic v1.x installed
- This causes: `ImportError: cannot import name 'Discriminator' from 'pydantic'`

## ✅ SOLUTION: Updated Script (No LiteLLM Required!)

I've updated `run_bench_ollama.sh` to use **Ollama's OpenAI-compatible API** instead of LiteLLM.

### Benefits:
- ✅ No Pydantic v2 dependency issues
- ✅ No LiteLLM required
- ✅ Uses the standard OpenAI client (already installed)
- ✅ Better error handling
- ✅ More reliable and faster

## Setup Instructions

### 1. Make Sure Ollama is Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### 2. Pull All Models (This will take time!)
```bash
ollama pull qwen3-next:80b      # ~48GB
ollama pull deepseek-r1:70b     # ~42GB
ollama pull deepseek-r1:32b     # ~19GB
ollama pull deepseek-r1:14b     # ~8.9GB
ollama pull deepseek-r1:8b      # ~4.9GB
```

### 3. Run the Benchmark
```bash
./run_bench_ollama.sh
```

## What Changed in the Script

### Old Version (Had Issues):
```bash
--llm-api litellm \
--model "ollama/${model}" \
```

### New Version (Works!):
```bash
export OPENAI_API_BASE="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama"  # Dummy key

--llm-api openai \
--model "${model}" \  # No "ollama/" prefix needed
```

## How It Works

Ollama provides an **OpenAI-compatible API** at `/v1` endpoint:
- `http://localhost:11434/v1/chat/completions` - Compatible with OpenAI's API
- The script uses the existing OpenAI client in llmperf
- No need for LiteLLM or Pydantic v2

## If You Still Want to Use LiteLLM

If you prefer LiteLLM for other reasons, fix the Pydantic issue:

```bash
# Option 1: Upgrade Pydantic
pip uninstall pydantic -y
pip install "pydantic>=2.0,<3.0"
pip install --upgrade litellm

# Option 2: Use specific versions
pip install pydantic==2.4.2 litellm==1.48.7
```

Then use the old script with `--llm-api litellm`.

## Expected Output

```
=========================================
Starting Ollama Benchmark
Testing 5 models with 7 concurrency levels
Using OpenAI-compatible API: http://localhost:11434/v1
Results will be saved to: results_ollama/benchmark_summary.csv
=========================================

=========================================
Testing Model: qwen3-next:80b
=========================================

  ┌─────────────────────────────────────┐
  │ Model: qwen3-next:80b
  │ Concurrency: 1
  └─────────────────────────────────────┘
  
[Progress bars and metrics...]
  
  ✓ Metrics extracted and saved to CSV
  ✓ Completed concurrency 1 for qwen3-next:80b
```

## Troubleshooting

### "Connection refused" error
```bash
# Make sure Ollama is running
ollama serve
```

### "Model not found" error
```bash
# Pull the model first
ollama pull qwen3-next:80b
```

### Script permission denied
```bash
chmod +x run_bench_ollama.sh
```

## Estimated Runtime

- **Per test**: 30-120 seconds
- **Total tests**: 5 models × 7 concurrency = 35 tests
- **Total time**: 30-90 minutes

Larger models (80b, 70b) will be slower than smaller ones (8b, 14b).

## View Results

```bash
# Simple view
cat results_ollama/benchmark_summary.csv

# Pretty table
column -t -s, results_ollama/benchmark_summary.csv | less -S
```

You're all set! 🚀
