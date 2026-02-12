# Ollama Benchmark - 簡化版使用指南

## 📋 概述

這個腳本完全遵循 `run_bench_vllm.sh` 的模式：
1. 運行 benchmark 測試
2. 使用 `collect_llmperf_table.py` 生成 CSV 表格

## 🚀 使用方法

### 1. 確保 Ollama 運行中
```bash
ollama serve
```

### 2. 拉取要測試的模型
```bash
ollama pull qwen3-next:80b
ollama pull deepseek-r1:70b
ollama pull deepseek-r1:32b
ollama pull deepseek-r1:14b
ollama pull deepseek-r1:8b
```

### 3. 運行 benchmark
```bash
./run_bench_ollama.sh
```

## 📊 輸出結果

每個模型會生成獨立的目錄和 CSV：

```
results_ollama_qwen3-next_80b/
├── concurrency_1/
│   ├── qwen3-next_80b_100_1024_summary.json
│   └── qwen3-next_80b_100_1024_individual_responses.json
├── concurrency_2/
├── ...
└── benchmark_table.csv  ← 主要結果表格

results_ollama_deepseek-r1_70b/
└── benchmark_table.csv

results_ollama_deepseek-r1_32b/
└── benchmark_table.csv

...
```

## 📈 CSV 表格包含的指標

與 vLLM benchmark 完全相同的格式：

- **NUMBER OF CONCURRENT**: 併發數
- **INPUT LENGTH**: 輸入 token 數
- **OUTPUT LENGTH**: 輸出 token 數
- **INITIAL (S)**: TTFT (Time to First Token) 平均值
- **TOKEN GENERATION SPEED**: 每個 token 的生成時間 (秒/token)
- **TOKENS/S/USER (OUT)**: 每個請求的輸出吞吐量
- **TOKENS/S/USER (OUT + INPUT)**: 每個請求的總吞吐量
- **THROUGHPUT/S**: 系統整體吞吐量 (tokens/秒)
- **TTFT P50/P95**: TTFT 的 50th/95th 百分位數
- **E2E MEAN/P50/P95**: End-to-End 延遲統計
- **ERROR RATE**: 錯誤率

## 🔧 關鍵修復

腳本包含了針對 Ollama 的重要修復：

```bash
--additional-sampling-params '{"max_tokens":1024,"options":{"num_predict":1024,"num_ctx":4096,"temperature":0.7,"top_p":0.9}}'
```

**為什麼需要這些參數？**
- `max_tokens`: OpenAI API 標準參數
- `options.num_predict`: Ollama 原生參數，控制生成 token 數
- `options.num_ctx`: Context window 大小，確保有足夠空間生成
- 兩者都設置確保兼容性

## 🎯 與 vLLM 腳本的對比

### run_bench_vllm.sh
```bash
for c in "${concurrencies[@]}"; do
  OUT_DIR="results_Mixtral_176B/concurrency_${c}"
  python token_benchmark_ray.py ...
done
# 然後手動運行: python collect_llmperf_table.py --base-dir results_Mixtral_176B
```

### run_bench_ollama.sh (新)
```bash
for model in "${models[@]}"; do
  for c in "${concurrencies[@]}"; do
    OUT_DIR="results_ollama_${model}/concurrency_${c}"
    python token_benchmark_ray.py ...
  done
  # 自動生成 CSV
  python collect_llmperf_table.py --base-dir "results_ollama_${model}"
done
```

**改進**：
- ✅ 支持多個模型
- ✅ 自動調用 `collect_llmperf_table.py`
- ✅ 每個模型獨立的結果目錄和 CSV

## 🧪 測試單個模型

如果只想測試一個模型，編輯腳本第 4-10 行：

```bash
models=(
  "deepseek-r1:8b"  # 只測試這一個
)
```

## 📝 查看結果

```bash
# 查看某個模型的結果
cat results_ollama_deepseek-r1_8b/benchmark_table.csv

# 或用 column 格式化顯示
column -t -s, results_ollama_deepseek-r1_8b/benchmark_table.csv | less -S
```

## ⏱️ 預估時間

- **deepseek-r1:8b**: ~20-40 分鐘
- **deepseek-r1:14b**: ~30-60 分鐘
- **deepseek-r1:32b**: ~1-2 小時
- **deepseek-r1:70b**: ~2-3 小時
- **qwen3-next:80b**: ~2-3 小時

**總計**: 約 6-10 小時（5 個模型 × 7 個併發級別）

## 💡 提示

1. **使用 tmux/screen** 避免斷線：
   ```bash
   tmux new -s ollama_bench
   ./run_bench_ollama.sh
   # Ctrl+B, D 分離
   ```

2. **監控進度**：
   ```bash
   # 查看最新生成的文件
   find results_ollama_* -name "*.json" -mmin -5
   ```

3. **只測試小模型先驗證**：
   ```bash
   models=("deepseek-r1:8b")  # 修改腳本
   concurrencies=("1" "4")     # 只測試 2 個併發級別
   ```

就是這麼簡單！🎉
