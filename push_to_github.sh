#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "🚀 Публікація гілки main у https://github.com/sshill/Hybrid-IDE-for-contributirs.git ..."
git push -u origin main
echo "✅ Репозиторій успішно опубліковано на GitHub!"
