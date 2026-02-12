#!/usr/bin/env python3
"""
診斷腳本：檢查 Ollama /v1/chat/completions streaming 回傳的真實格式。
只發一個請求，印出前 10 個 SSE chunk 的原始內容。
"""

import requests
import json
import os

OLLAMA_BASE = os.environ.get("OPENAI_API_BASE", "http://localhost:11434/v1")
url = OLLAMA_BASE.rstrip("/") + "/chat/completions"

body = {
    "model": "qwen3-next:80b",
    "messages": [
        {"role": "user", "content": "Hello, write a short poem about the sky."}
    ],
    "stream": True,
    "max_tokens": 100,
    "options": {
        "num_predict": 100,
        "num_ctx": 4096,
    },
}

headers = {"Authorization": "Bearer ollama", "Content-Type": "application/json"}

print(f"POST {url}")
print(f"Body: {json.dumps(body, indent=2)}")
print("=" * 60)

with requests.post(url, json=body, stream=True, timeout=120, headers=headers) as resp:
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print("=" * 60)

    chunk_count = 0
    generated_text = ""

    for raw_line in resp.iter_lines(chunk_size=None):
        chunk_count += 1
        
        # Show raw bytes
        print(f"\n--- Chunk {chunk_count} ---")
        print(f"  raw bytes : {raw_line!r}")
        print(f"  type      : {type(raw_line)}")
        
        stripped = raw_line.strip()
        if not stripped:
            print(f"  → EMPTY LINE (skipped)")
            continue

        # Check if it starts with "data: "
        decoded = stripped.decode("utf-8", errors="replace") if isinstance(stripped, bytes) else stripped
        print(f"  decoded   : {decoded[:200]}")
        
        has_data_prefix = decoded.startswith("data: ")
        print(f"  has 'data: ' prefix: {has_data_prefix}")
        
        if decoded == "data: [DONE]":
            print(f"  → [DONE] signal")
            continue

        # Try to parse JSON
        json_str = decoded[len("data: "):] if has_data_prefix else decoded
        try:
            data = json.loads(json_str)
            print(f"  parsed JSON keys: {list(data.keys())}")
            
            if "choices" in data:
                choices = data["choices"]
                print(f"  choices[0] keys: {list(choices[0].keys())}")
                
                if "delta" in choices[0]:
                    delta = choices[0]["delta"]
                    print(f"  delta keys: {list(delta.keys())}")
                    print(f"  delta content: {delta.get('content', '<<MISSING>>')!r}")
                    
                    content = delta.get("content", None)
                    if content:
                        generated_text += content
                elif "message" in choices[0]:
                    msg = choices[0]["message"]
                    print(f"  message keys: {list(msg.keys())}")
                    print(f"  message content: {msg.get('content', '<<MISSING>>')!r}")
                else:
                    print(f"  choices[0] = {choices[0]}")
            else:
                print(f"  Full data: {json.dumps(data, indent=2)[:300]}")
                
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            print(f"  attempted to parse: {json_str[:200]!r}")

        # Stop after 15 chunks to avoid flooding
        if chunk_count >= 15:
            print("\n... (stopped after 15 chunks)")
            break

print("\n" + "=" * 60)
print(f"Total chunks seen: {chunk_count}")
print(f"Generated text so far: {generated_text!r}")
print(f"Generated text length: {len(generated_text)}")
