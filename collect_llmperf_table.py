#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Read llmperf outputs under concurrency_* folders.
Print a DataFrame with SAME columns as screenshot + extra columns, and save CSV.

Key change:
- THROUGHPUT/S is taken ONLY from summary.json:
  results_mean_output_throughput_token_per_s  (wall-clock throughput computed by llmperf)
- No fallback. If missing -> raise error.

Usage:
  python collect_llmperf_table.py --base-dir results_vllm --out llmperf_table.csv
"""

import argparse
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd


def safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def safe_int(x) -> Optional[int]:
    try:
        return int(float(x))
    except Exception:
        return None


def quantiles(arr, qs=(0.5, 0.95)) -> Dict[float, float]:
    arr = np.array(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {q: float("nan") for q in qs}
    return {q: float(np.quantile(arr, q)) for q in qs}


def mean(arr) -> float:
    arr = np.array(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if arr.size else float("nan")


def flatten_inter_token_latency(values: List[Any]) -> np.ndarray:
    out: List[float] = []
    for v in values:
        if v is None:
            continue
        if isinstance(v, list):
            out.extend([safe_float(i) for i in v])
        else:
            out.append(safe_float(v))
    arr = np.array(out, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return np.array([float("nan")], dtype=float)
    return arr


def infer_concurrency_from_folder(folder: Path) -> int:
    m = re.search(r"concurrency[_\- ](\d+)", folder.name)
    return int(m.group(1)) if m else -1


def find_one(folder: Path, pattern: str) -> Optional[Path]:
    hits = sorted(folder.glob(pattern))
    return hits[0] if hits else None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_metrics_for_folder(concurrency_dir: Path) -> Optional[Dict[str, Any]]:
    summary_path = find_one(concurrency_dir, "*_summary.json")
    indiv_path = find_one(concurrency_dir, "*_individual_responses.json")
    if summary_path is None or indiv_path is None:
        return None

    summary = load_json(summary_path)
    indiv = load_json(indiv_path)

    total_requests = len(indiv)

    valid: List[Dict[str, Any]] = []
    errored = 0
    error_codes: Dict[str, int] = {}

    for r in indiv:
        err = r.get("error_code")
        if err not in (None, 0, "", "0"):
            errored += 1
            error_codes[str(err)] = error_codes.get(str(err), 0) + 1
            continue

        e2e = safe_float(r.get("end_to_end_latency_s"))
        out_toks = safe_float(r.get("number_output_tokens"))
        in_toks = safe_float(r.get("number_input_tokens"))

        if not np.isfinite(e2e) or e2e <= 0:
            errored += 1
            error_codes["bad_e2e"] = error_codes.get("bad_e2e", 0) + 1
            continue
        if not np.isfinite(out_toks) or out_toks <= 0:
            errored += 1
            error_codes["bad_out_tokens"] = error_codes.get("bad_out_tokens", 0) + 1
            continue
        if not np.isfinite(in_toks) or in_toks < 0:
            errored += 1
            error_codes["bad_in_tokens"] = error_codes.get("bad_in_tokens", 0) + 1
            continue

        valid.append(r)

    # ---- THROUGHPUT/S (wall-clock) from summary only ----
    # llmperf summary key is flattened as: results_mean_output_throughput_token_per_s
    thr_key = "results_mean_output_throughput_token_per_s"
    if thr_key not in summary:
        raise KeyError(
            f"[{concurrency_dir}] Missing '{thr_key}' in summary.json. "
            "This script does NOT fallback. Please re-run benchmark to generate correct summary."
        )
    throughput_s = safe_float(summary.get(thr_key))
    if not np.isfinite(throughput_s):
        raise ValueError(
            f"[{concurrency_dir}] '{thr_key}' is not a finite number: {summary.get(thr_key)}"
        )

    if not valid:
        c = infer_concurrency_from_folder(concurrency_dir)
        return {
            "NUMBER OF CONCURRENT": c,
            "INPUT LENGTH": float("nan"),
            "OUTPUT LENGTH": float("nan"),
            "INITIAL (S)": float("nan"),
            "TOKEN GENERATION SPEED": float("nan"),
            "TOKENS/S/USER (OUT)": float("nan"),
            "TOKENS/S/USER (OUT + INPUT)": float("nan"),
            "THROUGHPUT/S": float(throughput_s),

            "VALID REQUESTS": 0,
            "TOTAL REQUESTS": total_requests,
            "ERROR REQUESTS": errored,
            "ERROR RATE": (errored / total_requests) if total_requests else float("nan"),
            "ERROR CODES": json.dumps(error_codes, ensure_ascii=False),
            "MODEL": str(summary.get("model", "")),
            "FOLDER": str(concurrency_dir),
        }

    # Arrays
    ttft = np.array([safe_float(r.get("ttft_s")) for r in valid], dtype=float)
    e2e = np.array([safe_float(r.get("end_to_end_latency_s")) for r in valid], dtype=float)
    out_toks = np.array([safe_float(r.get("number_output_tokens")) for r in valid], dtype=float)
    in_toks = np.array([safe_float(r.get("number_input_tokens")) for r in valid], dtype=float)
    total_toks = in_toks + out_toks

    inter_vals = flatten_inter_token_latency([r.get("inter_token_latency_s") for r in valid])

    # concurrency
    c = infer_concurrency_from_folder(concurrency_dir)
    for k in ("num_concurrent_requests", "concurrency", "num_concurrent"):
        if k in summary:
            v = safe_int(summary.get(k))
            if v is not None:
                c = v
                break

    # screenshot columns (mean)
    input_len = int(round(mean(in_toks)))
    output_len = int(round(mean(out_toks)))
    initial_mean = mean(ttft)                 # TTFT mean
    token_gen_s_per_tok = mean(inter_vals)    # s/token (matches screenshot look)

    tokens_per_s_user_out = mean(out_toks / e2e)
    tokens_per_s_user_total = mean(total_toks / e2e)

    # extra columns (more detail)
    ttft_q = quantiles(ttft, qs=(0.5, 0.95))
    e2e_q = quantiles(e2e, qs=(0.5, 0.95))
    tokgen_tok_s = (1.0 / token_gen_s_per_tok) if (np.isfinite(token_gen_s_per_tok) and token_gen_s_per_tok > 0) else float("nan")
    error_rate = (errored / total_requests) if total_requests else float("nan")

    row = {
        # EXACT screenshot columns
        "NUMBER OF CONCURRENT": c,
        "INPUT LENGTH": input_len,
        "OUTPUT LENGTH": output_len,
        "INITIAL (S)": float(initial_mean),
        "TOKEN GENERATION SPEED": float(token_gen_s_per_tok),
        "TOKENS/S/USER (OUT)": float(tokens_per_s_user_out),
        "TOKENS/S/USER (OUT + INPUT)": float(tokens_per_s_user_total),
        "THROUGHPUT/S": float(throughput_s),

        # More detailed columns
        "VALID REQUESTS": int(len(valid)),
        "TOTAL REQUESTS": int(total_requests),
        "ERROR REQUESTS": int(errored),
        "ERROR RATE": float(error_rate),

        "TTFT P50 (S)": float(ttft_q[0.5]),
        "TTFT P95 (S)": float(ttft_q[0.95]),
        "E2E MEAN (S)": float(mean(e2e)),
        "E2E P50 (S)": float(e2e_q[0.5]),
        "E2E P95 (S)": float(e2e_q[0.95]),
        "TOKEN GEN SPEED (TOK/S)": float(tokgen_tok_s),

        "ERROR CODES": json.dumps(error_codes, ensure_ascii=False),
        "MODEL": str(summary.get("model", "")),
        "FOLDER": str(concurrency_dir),
    }
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", type=str, default="results_vllm",
                    help="Directory containing concurrency_* folders (default: results_vllm)")
    ap.add_argument("--out", type=str, default="llmperf_table.csv",
                    help="Output CSV file (default: llmperf_table.csv)")
    ap.add_argument("--round", type=int, default=6,
                    help="Decimal rounding for printed table (default: 6)")
    args = ap.parse_args()

    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        raise FileNotFoundError(f"Base dir not found: {base_dir.resolve()}")

    conc_dirs = sorted([p for p in base_dir.glob("concurrency_*") if p.is_dir()])
    if not conc_dirs:
        conc_dirs = sorted([p for p in base_dir.rglob("concurrency_*") if p.is_dir()])
    if not conc_dirs:
        raise RuntimeError(f"No concurrency_* folders found under: {base_dir.resolve()}")

    rows = []
    for d in conc_dirs:
        row = compute_metrics_for_folder(d)
        if row is not None:
            rows.append(row)

    df = pd.DataFrame(rows)

    if "NUMBER OF CONCURRENT" in df.columns:
        df = df.sort_values("NUMBER OF CONCURRENT")

    # Round float columns
    round_cols = [
        "INITIAL (S)",
        "TOKEN GENERATION SPEED",
        "TOKENS/S/USER (OUT)",
        "TOKENS/S/USER (OUT + INPUT)",
        "THROUGHPUT/S",
        "TTFT P50 (S)",
        "TTFT P95 (S)",
        "E2E MEAN (S)",
        "E2E P50 (S)",
        "E2E P95 (S)",
        "TOKEN GEN SPEED (TOK/S)",
        "ERROR RATE",
    ]
    for c in round_cols:
        if c in df.columns:
            df[c] = df[c].astype(float).round(args.round)

    # Put screenshot columns first
    screenshot_cols = [
        "NUMBER OF CONCURRENT",
        "INPUT LENGTH",
        "OUTPUT LENGTH",
        "INITIAL (S)",
        "TOKEN GENERATION SPEED",
        "TOKENS/S/USER (OUT)",
        "TOKENS/S/USER (OUT + INPUT)",
        "THROUGHPUT/S",
    ]
    extra_cols = [c for c in df.columns if c not in screenshot_cols]
    df = df[screenshot_cols + extra_cols]

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 260)
    print(df.to_string(index=False))

    out_path = Path(args.out)
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\nSaved CSV: {out_path.resolve()}")


if __name__ == "__main__":
    main()