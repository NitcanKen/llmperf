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

# Create main results directory
MAIN_RESULTS_DIR="results_ollama"
mkdir -p "${MAIN_RESULTS_DIR}"

# CSV output file
CSV_FILE="${MAIN_RESULTS_DIR}/benchmark_summary.csv"

# Initialize CSV with headers
echo "Model,Concurrency,NumCompletedRequests,TTFT_Mean(s),TTFT_P50(s),TTFT_P99(s),TokenGenSpeed_Mean(tok/s),TokenGenSpeed_P50(tok/s),TokenGenSpeed_P99(tok/s),E2E_Mean(s),E2E_P50(s),E2E_P99(s),Throughput(tok/s),ErrorRate" > "${CSV_FILE}"

echo "========================================="
echo "Starting Ollama Benchmark"
echo "Testing ${#models[@]} models with ${#concurrencies[@]} concurrency levels"
echo "Using OpenAI-compatible API: ${OPENAI_API_BASE}"
echo "Results will be saved to: ${CSV_FILE}"
echo "========================================="

# Loop through each model
for model in "${models[@]}"; do
  echo ""
  echo "========================================="
  echo "Testing Model: ${model}"
  echo "========================================="
  
  # Sanitize model name for directory/file naming
  model_safe=$(echo "${model}" | sed 's/:/_/g' | sed 's/\//_/g')
  
  # Loop through each concurrency level
  for c in "${concurrencies[@]}"; do
    echo ""
    echo "  ┌─────────────────────────────────────┐"
    echo "  │ Model: ${model}"
    echo "  │ Concurrency: ${c}"
    echo "  └─────────────────────────────────────┘"
    
    # Create output directory for this specific test
    OUT_DIR="${MAIN_RESULTS_DIR}/${model_safe}/concurrency_${c}"
    mkdir -p "${OUT_DIR}"
    
    # Run the benchmark using OpenAI API (Ollama is OpenAI-compatible)
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
      --metadata "backend=ollama,model=${model},concurrency=${c}" \
      --additional-sampling-params '{}' || {
        echo "  ✗ Error running benchmark for ${model} at concurrency ${c}"
        echo "${model},${c},0,0,0,0,0,0,0,0,0,0,0,1.0" >> "${CSV_FILE}"
        continue
      }
    
    # Extract metrics from JSON and append to CSV
    # Find the summary JSON file
    SUMMARY_JSON=$(find "${OUT_DIR}" -name "*_summary.json" -type f | head -n 1)
    
    if [ -f "${SUMMARY_JSON}" ]; then
      # Extract metrics using Python
      python3 << EOF
import json
import sys

try:
    with open("${SUMMARY_JSON}", "r") as f:
        data = json.load(f)
    
    results = data.get("results", {})
    
    # Extract metrics
    model_name = "${model}"
    concurrency = "${c}"
    num_completed = results.get("num_completed_requests", 0)
    
    # TTFT (Time to First Token)
    ttft = results.get("ttft_s", {})
    ttft_mean = ttft.get("mean", 0)
    ttft_p50 = ttft.get("quantiles", {}).get("p50", 0)
    ttft_p99 = ttft.get("quantiles", {}).get("p99", 0)
    
    # Token Generation Speed (Request Output Throughput)
    token_speed = results.get("request_output_throughput_token_per_s", {})
    token_speed_mean = token_speed.get("mean", 0)
    token_speed_p50 = token_speed.get("quantiles", {}).get("p50", 0)
    token_speed_p99 = token_speed.get("quantiles", {}).get("p99", 0)
    
    # E2E Latency
    e2e = results.get("end_to_end_latency_s", {})
    e2e_mean = e2e.get("mean", 0)
    e2e_p50 = e2e.get("quantiles", {}).get("p50", 0)
    e2e_p99 = e2e.get("quantiles", {}).get("p99", 0)
    
    # Overall Throughput
    throughput = results.get("mean_output_throughput_token_per_s", 0)
    
    # Error Rate
    error_rate = results.get("error_rate", 0)
    
    # Write to CSV
    csv_line = f"{model_name},{concurrency},{num_completed},{ttft_mean:.4f},{ttft_p50:.4f},{ttft_p99:.4f},{token_speed_mean:.4f},{token_speed_p50:.4f},{token_speed_p99:.4f},{e2e_mean:.4f},{e2e_p50:.4f},{e2e_p99:.4f},{throughput:.4f},{error_rate:.4f}"
    
    with open("${CSV_FILE}", "a") as csv_file:
        csv_file.write(csv_line + "\n")
    
    print(f"  ✓ Metrics extracted and saved to CSV")
    
except Exception as e:
    print(f"  ✗ Error extracting metrics: {e}", file=sys.stderr)
    # Write error row to CSV
    with open("${CSV_FILE}", "a") as csv_file:
        csv_file.write(f"${model},${c},0,0,0,0,0,0,0,0,0,0,0,1.0\n")
    sys.exit(1)
EOF
    else
      echo "  ✗ Warning: Summary JSON not found in ${OUT_DIR}"
      echo "${model},${c},0,0,0,0,0,0,0,0,0,0,0,1.0" >> "${CSV_FILE}"
    fi
    
    echo "  ✓ Completed concurrency ${c} for ${model}"
  done
  
  echo ""
  echo "✓ Completed all tests for ${model}"
  echo "========================================="
done

echo ""
echo "========================================="
echo "All benchmarks completed!"
echo "Summary CSV: ${CSV_FILE}"
echo "========================================="
echo ""
echo "To view the results:"
echo "  cat ${CSV_FILE}"
echo "  # or"
echo "  column -t -s, ${CSV_FILE} | less -S"
