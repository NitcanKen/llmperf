# Fix for Pydantic/LiteLLM Compatibility Issue

## Problem
The error occurs because:
1. Modern LiteLLM (v0.1.738+) requires **Pydantic v2.x** with `Discriminator` feature
2. The project's `pyproject.toml` specifies `pydantic<2.5` (which allows v2.0-2.4)
3. However, the installed Pydantic version is likely v1.x, causing the import error

## Solution: Update Pydantic to v2.x

### Option 1: Quick Fix (Recommended)
```bash
# Uninstall old pydantic
pip uninstall pydantic -y

# Install Pydantic v2.4 (highest allowed by pyproject.toml)
pip install "pydantic>=2.0,<2.5"

# Reinstall litellm to ensure compatibility
pip install --upgrade "litellm>=1.0.0"

# Verify installation
python -c "from pydantic import Discriminator; print('Pydantic v2 OK')"
```

### Option 2: Update pyproject.toml (If you control the project)
Edit `pyproject.toml` line 12:
```toml
# Change from:
dependencies = ["pydantic<2.5",

# To:
dependencies = ["pydantic>=2.0,<3.0",
```

Then reinstall:
```bash
pip install -e .
```

### Option 3: Use Specific Compatible Versions
```bash
pip uninstall pydantic litellm -y
pip install pydantic==2.4.2
pip install litellm==1.48.7
```

## Verify the Fix

After applying the fix, test the import:
```bash
python -c "from litellm import completion, validate_environment; print('LiteLLM OK')"
```

## Then Re-run the Benchmark
```bash
./run_bench_ollama.sh
```

## Additional Notes

- **Ray compatibility**: Ray works fine with Pydantic v2.x in Python 3.10
- **Breaking changes**: Pydantic v2 has some API changes, but LiteLLM handles them
- **If other errors occur**: Some older dependencies might need updates too

## Alternative: Use OpenAI-Compatible API

If Pydantic issues persist, you can use Ollama's OpenAI-compatible API directly:

```bash
# Modify the script to use openai API instead of litellm
# Change line 57 in run_bench_ollama.sh:
--llm-api openai \  # instead of litellm

# Set environment variable:
export OPENAI_API_BASE="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama"  # dummy key, Ollama doesn't require it
```

This bypasses LiteLLM entirely and uses the OpenAI client to talk to Ollama.
