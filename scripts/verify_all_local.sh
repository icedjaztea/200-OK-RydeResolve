#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
export PYTHONPATH=.
echo '1. Policy and routing-index integrity'
python scripts/check_contract.py
echo '2. Python unit/integration tests'
pytest -q
echo '3. Independent synthetic-policy regression'
python scripts/evaluate.py
echo '4. Synthetic prompt-injection boundary tests'
python scripts/threat_eval.py
echo 'Backend offline verification complete. Live ADK/cloud/Next.js checks are separate.'
