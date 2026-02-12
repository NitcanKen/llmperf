#!/usr/bin/env bash
set -e

# Models to test on Ollama
models=(
  "qwen3-next:80b"
  "deepseek-r1:70b"
  "deepseek-r1:32b"
  "deepseek-r1:14b"
  "deepseek-r1:8b"
)

# Concurrency levels to test
concurrencies=("1" "2" "4" "8" "16" "32" "64")

# Maximum number of requests per concurrency level
MAX_REQUESTS=32

# Ollama OpenAI-compatible API endpoint
export OPENAI_API_BASE="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama"  # Dummy key - Ollama doesn't require authentication

echo "========================================="
echo "Ollama Benchmark"
echo "Testing ${#models[@]} models with ${#concurrencies[@]} concurrency levels"
echo "Using OpenAI-compatible API: ${OPENAI_API_BASE}"
echo "========================================="

# Loop through each model
for model in "${models[@]}"; do
  echo ""
  echo "========================================="
  echo "Testing Model: ${model}"
  echo "========================================="
  
  # Sanitize model name for directory naming
  model_safe=$(echo "${model}" | sed 's/:/_/g' | sed 's/\//_/g')
  BASE_DIR="results_ollama_${model_safe}"
  
  # Loop through each concurrency level
  for c in "${concurrencies[@]}"; do
    echo ""
    echo "Running benchmark: ${model}, concurrency = ${c}"
    
    OUT_DIR="${BASE_DIR}/concurrency_${c}"
    mkdir -p "${OUT_DIR}"
    
    # Run the benchmark
    # Note: Ollama needs num_predict and num_ctx in options for proper token generation
    python token_benchmark_ray.py \
      --model "${model}" \
      --llm-api openai \
      --mean-input-tokens 100 \
      --stddev-input-tokens 0 \
      --mean-output-tokens 1024 \
      --stddev-output-tokens 0 \
      --max-num-completed-requests "${MAX_REQUESTS}" \
      --timeout 120000 \
      --num-concurrent-requests "${c}" \
      --results-dir "${OUT_DIR}" \
      --metadata "backend=ollama,concurrency=${c}" \
      --additional-sampling-params '{"max_tokens":1024,"options":{"num_predict":1024,"num_ctx":4096,"temperature":0.7,"top_p":0.9}}'
  done
  
  echo ""
  echo "✓ Completed all tests for ${model}"
  echo "Generating CSV table..."
  
  # Generate CSV using collect_llmperf_table.py
  python collect_llmperf_table.py \
    --base-dir "${BASE_DIR}" \
    --out "${BASE_DIR}/benchmark_table.csv"
  
  echo "========================================="
done

echo ""
echo "========================================="
echo "All benchmarks completed!"
echo ""
echo "Results saved in:"
for model in "${models[@]}"; do
  model_safe=$(echo "${model}" | sed 's/:/_/g' | sed 's/\//_/g')
  echo "  - results_ollama_${model_safe}/benchmark_table.csv"
done
echo "========================================="
