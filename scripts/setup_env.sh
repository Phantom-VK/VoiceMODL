#!/usr/bin/env bash
# Bootstrap a local virtual environment and install Python deps for VoiceModL.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"

python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    echo "python3 not found. Please install Python 3.10+." >&2
    return 1
  fi
}

PYTHON="$(python_bin)"

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
