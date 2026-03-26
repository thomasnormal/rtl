#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${1:-$ROOT_DIR/third_party}"

mkdir -p "$DATA_DIR"

clone_or_update_branch() {
  local url="$1"
  local name="$2"
  local branch="$3"
  local dest="$DATA_DIR/$name"

  if [[ -d "$dest/.git" ]]; then
    echo "Updating $name"
    git -C "$dest" pull --ff-only --depth 1 origin "$branch"
  else
    echo "Cloning $name"
    git clone --depth 1 --branch "$branch" "$url" "$dest"
  fi
}

clone_or_update_branch "https://github.com/hkust-zhiyao/RTLLM.git" "RTLLM-v1.1" "v1.1"
clone_or_update_branch "https://github.com/hkust-zhiyao/RTLLM.git" "RTLLM-v2.0" "main"
clone_or_update_branch "https://github.com/NVlabs/verilog-eval.git" "verilog-eval" "main"
clone_or_update_branch "https://github.com/hkust-zhiyao/AssertLLM.git" "AssertLLM" "main"
clone_or_update_branch "https://github.com/AUCOHL/RTL-Repo.git" "RTL-Repo" "main"

echo
echo "Seed datasets are available under: $DATA_DIR"
echo "Next recommended checks:"
echo "  python -c \"from rtl_training.task_store import store_rtllm_tasks; store_rtllm_tasks('$DATA_DIR/RTLLM-v1.1', '$ROOT_DIR/data/task_store', dataset_name='rtllm_v1_1')\""
echo "  python -c \"from rtl_training.task_store import store_rtllm_tasks; store_rtllm_tasks('$DATA_DIR/RTLLM-v2.0', '$ROOT_DIR/data/task_store', dataset_name='rtllm_v2_0')\""
echo "  python -c \"from rtl_training.task_store import store_verilog_eval_tasks; store_verilog_eval_tasks('$DATA_DIR/verilog-eval', '$ROOT_DIR/data/task_store', dataset_name='verilogeval_v2_spec_to_rtl')\""
