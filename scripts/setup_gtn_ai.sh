#!/usr/bin/env bash
set -euo pipefail

AI_ROOT="${GTN_AI_ROOT:-/opt/gtn-ai-runtime}"
AI_VENV="${GTN_AI_VENV:-/opt/gtn-ai-venv}"
AI_DATA_ROOT="${GTN_AI_DATA_ROOT:-/var/lib/gtn-ai}"
AI_ENV_FILE="${GTN_AI_ENV_FILE:-/etc/gtn/ai.env}"
AI_RUNTIME_ARCHIVE="${GTN_AI_RUNTIME_ARCHIVE:-}"
AI_CHECKPOINT_NAME="${GTN_AI_CHECKPOINT_NAME:-structured-v2-search-dagger-v2.epoch-06.pt}"
AI_CHECKPOINT="${GTN_AI_CHECKPOINT:-${AI_ROOT}/models/${AI_CHECKPOINT_NAME}}"
BOOTSTRAP_PYTHON="${GTN_AI_BOOTSTRAP_PYTHON:-python3}"
TORCH_INDEX_URL="${GTN_AI_TORCH_INDEX_URL:-https://mirrors.aliyun.com/pytorch-wheels/cpu}"

if [[ -z "${AI_RUNTIME_ARCHIVE}" ]]; then
  echo "GTN_AI_RUNTIME_ARCHIVE must point to a production runtime bundle." >&2
  exit 2
fi

if [[ "${AI_RUNTIME_ARCHIVE}" =~ ^https?:// ]]; then
  ARCHIVE_PATH="$(mktemp /tmp/gtn-ai-runtime.XXXXXX.tar.gz)"
  curl --fail --location "${AI_RUNTIME_ARCHIVE}" --output "${ARCHIVE_PATH}"
  REMOVE_ARCHIVE=1
else
  ARCHIVE_PATH="${AI_RUNTIME_ARCHIVE}"
  REMOVE_ARCHIVE=0
fi
if [[ ! -f "${ARCHIVE_PATH}" ]]; then
  echo "Missing AI runtime bundle: ${ARCHIVE_PATH}" >&2
  exit 2
fi

STAGING_DIR="$(mktemp -d "$(dirname "${AI_ROOT}")/gtn-ai-runtime.XXXXXX")"
cleanup() {
  rm -rf "${STAGING_DIR}"
  if [[ "${REMOVE_ARCHIVE}" == "1" ]]; then rm -f "${ARCHIVE_PATH}"; fi
}
trap cleanup EXIT
tar -xzf "${ARCHIVE_PATH}" -C "${STAGING_DIR}"
EXTRACTED_ROOT="${STAGING_DIR}/gtn-ai-runtime"
if [[ ! -f "${EXTRACTED_ROOT}/gtn_ai/live_worker.py" ]]; then
  echo "Invalid AI runtime bundle: live worker missing." >&2
  exit 2
fi
if [[ ! -f "${EXTRACTED_ROOT}/models/${AI_CHECKPOINT_NAME}" ]]; then
  echo "Invalid AI runtime bundle: checkpoint missing." >&2
  exit 2
fi

"${BOOTSTRAP_PYTHON}" -m venv "${AI_VENV}"
"${AI_VENV}/bin/python" -m pip install --upgrade pip setuptools wheel
"${AI_VENV}/bin/python" -m pip install \
  --index-url "${TORCH_INDEX_URL}" torch==2.10.0

rm -rf "${AI_ROOT}.previous"
if [[ -e "${AI_ROOT}" ]]; then mv "${AI_ROOT}" "${AI_ROOT}.previous"; fi
mv "${EXTRACTED_ROOT}" "${AI_ROOT}"
rm -rf "${AI_ROOT}.previous"

install -d -m 0750 "${AI_DATA_ROOT}/runtime" "${AI_DATA_ROOT}/human-sessions" \
  "$(dirname "${AI_ENV_FILE}")"
(cd "${AI_ROOT}" && "${AI_VENV}/bin/python" -c \
  "from gtn_ai.live_worker import default_policy_name; print(default_policy_name())")

cat >"${AI_ENV_FILE}" <<EOF
GTN_AI_1V1_TEST_ENABLED=1
GTN_AI_ROOT=${AI_ROOT}
GTN_AI_PYTHON=${AI_VENV}/bin/python
GTN_AI_RUNTIME_ROOT=${AI_DATA_ROOT}/runtime
GTN_AI_DIAGNOSTICS_ROOT=${AI_DATA_ROOT}/human-sessions
GTN_AI_1V1_MAX_ACTIVE=5
GTN_AI_MAX_PARALLEL_DECISIONS=1
GTN_AI_MAX_SESSIONS=8
GTN_AI_DIAGNOSTIC_RETENTION_DAYS=14
GTN_AI_DIAGNOSTIC_MAX_GB=2
GTN_AI_EXPORT_FINISHED=0
GTN_AI_LIVE_POLICY=unsafe-rollout-cpu:${AI_CHECKPOINT};candidates=3;rollouts=2;horizon=2;belief=true;exploration=0
EOF
chmod 0640 "${AI_ENV_FILE}"

echo "GTN-AI is ready. Attach ${AI_ENV_FILE} to the game service and restart it."
