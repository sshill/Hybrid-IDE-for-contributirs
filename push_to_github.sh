#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

COMMIT_SHA=$(git rev-parse HEAD)
echo "🚀 Публікація гілки main (${COMMIT_SHA:0:7}) у https://github.com/sshill/Hybrid-IDE-for-contributirs.git ..."
git push -u origin main --force-with-lease

echo ""
echo "🔍 Фаза 5: Хмарна верифікація GitHub Actions CI (policy_ci.yml)..."
python3 "${SCRIPT_DIR}/core/verify/verify_remote_ci.py" --commit "${COMMIT_SHA}"
