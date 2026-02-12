#!/usr/bin/env bash
set -e

# 要測的併發數
concurrencies=("1" "2" "4" "8" "16" "32" "64")

# !!! 要改的地方：MODEL_NAME 要和你 vLLM 啟動時用的一樣 !!!
MODEL_NAME="MaziyarPanahi/Mixtral-8x22B-Instruct-v0.1-AWQ"

# 每個併發下最多完成多少 request
MAX_REQUESTS=32

for c in "${concurrencies[@]}"; do
  echo "==============================="
  echo "Running benchmark, concurrency = ${c}"
  echo "==============================="

  OUT_DIR="results_Mixtral_176B/concurrency_${c}"
  mkdir -p "${OUT_DIR}"

  python token_benchmark_ray.py \
    --model "${MODEL_NAME}" \
    --llm-api openai \
    --mean-input-tokens 100 \
    --stddev-input-tokens 0 \
    --mean-output-tokens 1024 \
    --stddev-output-tokens 0 \
    --max-num-completed-requests "${MAX_REQUESTS}" \
    --timeout 120000 \
    --num-concurrent-requests "${c}" \
    --results-dir "${OUT_DIR}" \
    --metadata "backend=vllm,concurrency=${c}" \
    --additional-sampling-params '{}'
done
