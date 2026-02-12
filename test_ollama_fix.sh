#!/usr/bin/env bash

echo "========================================="
echo "Ollama Token Generation 修復測試"
echo "========================================="
echo ""

MODEL="qwen3-next:80b"

echo "測試 1: 使用 max_tokens（原始方式 - 可能失敗）"
echo "-----------------------------------------"
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"請寫一個至少 200 字的故事：\"}],
    \"max_tokens\": 1024,
    \"stream\": false
  }" | jq -r '.choices[0].message.content' | wc -w
echo ""

echo "測試 2: 使用 options.num_predict（推薦方式）"
echo "-----------------------------------------"
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"請寫一個至少 200 字的故事：\"}],
    \"max_tokens\": 1024,
    \"options\": {
      \"num_predict\": 1024,
      \"num_ctx\": 4096,
      \"temperature\": 0.7,
      \"top_p\": 0.9
    },
    \"stream\": false
  }" | jq -r '.choices[0].message.content' | wc -w
echo ""

echo "測試 3: Ollama 原生 API（對照組）"
echo "-----------------------------------------"
curl -s http://localhost:11434/api/generate -d "{
  \"model\": \"${MODEL}\",
  \"prompt\": \"請寫一個至少 200 字的故事：\",
  \"stream\": false,
  \"options\": {
    \"num_predict\": 1024,
    \"num_ctx\": 4096,
    \"temperature\": 0.7
  }
}" | jq -r '.response' | wc -w
echo ""

echo "========================================="
echo "如果測試 2 和測試 3 生成了大量 tokens（>100），"
echo "而測試 1 只生成少量 tokens，則修復成功！"
echo "========================================="
