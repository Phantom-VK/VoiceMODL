#!/usr/bin/env bash
# Bootstrap a local virtual environment and install Python deps for VoiceModL.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"

choose_python() {
  local candidates=()

  # User override first
  if [[ -n "${PYTHON-}" ]]; then
    candidates+=("${PYTHON}")
  fi

  # Common system interpreters (ordered by preference)
  candidates+=(python3 python3.13 python3.12 python3.11 python3.10 python3.9)
  candidates+=(/usr/bin/python3 /usr/bin/python3.9)
  candidates+=(/home/vikramaditya/micromamba/bin/python3.9)

  for candidate in "${candidates[@]}"; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      # ensure ssl module is importable
      if "${candidate}" - <<'PY' >/dev/null 2>&1
import ssl
PY
      then
        command -v "${candidate}"
        return 0
      fi
    fi
  done

  return 1
}

PYTHON="$(choose_python || true)"
if [[ -z "${PYTHON}" ]]; then
  echo "No usable Python (with ssl module) found. Install Python 3.9+ with OpenSSL support." >&2
  exit 1
fi

echo "[setup] Using python at: ${PYTHON}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[setup] Creating virtualenv at ${VENV_DIR}"
  "${PYTHON}" -m venv "${VENV_DIR}"
else
  echo "[setup] Reusing existing virtualenv at ${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
echo "[setup] Python version: $(python --version)"

pip install --upgrade pip wheel setuptools

REQ_FILE="${PROJECT_ROOT}/requirements.txt"
if [[ ! -f "${REQ_FILE}" ]]; then
  echo "requirements.txt not found at ${REQ_FILE}" >&2
  exit 1
fi

echo "[setup] Installing dependencies from requirements.txt"
pip install -r "${REQ_FILE}"

cat <<'EOF'
------------------------------------------
Environment ready.
If pitch shifting via pyrubberband fails, install the Rubber Band CLI libs:
  sudo apt-get install rubberband-cli librubberband-dev
Then rerun this script.
------------------------------------------
EOF
