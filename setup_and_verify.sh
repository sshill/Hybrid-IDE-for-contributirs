#!/usr/bin/env bash
# ==============================================================================
# Hybrid Agentic IDE: Автоматизований скрипт розгортання та валідації середовища
# Для ОС: Debian 13 (Trixie) Linux / Ubuntu / Linux x86_64
# ==============================================================================

set -u

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}🚀 Hybrid Agentic IDE: Перевірка та ініціалізація середовища (v0.8.3)${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Перевірка операційної системи
echo -e "\n${BLUE}[1/6] Перевірка операційної системи...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "  ОС: ${GREEN}${PRETTY_NAME:-Linux}${NC}"
else
    echo -e "  ${YELLOW}⚠️ Не вдалося визначити точну версію ОС через /etc/os-release.${NC}"
fi

# 2. Перевірка базових системних утиліт
echo -e "\n${BLUE}[2/6] Перевірка системних пакетів (Python, Git, Curl)...${NC}"
for cmd in python3 git curl; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo -e "  🟢 $cmd: ${GREEN}$(command -v "$cmd")${NC}"
    else
        echo -e "  ${RED}❌ $cmd не знайдено! Встановіть через: sudo apt install -y $cmd${NC}"
        exit 1
    fi
done

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  Версія Python: ${GREEN}${PY_VER}${NC} (потрібно >= 3.10)"

# 3. Перевірка локального демона Ollama
echo -e "\n${BLUE}[3/6] Перевірка локального сервісу Ollama (Tier 1)...${NC}"
if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo -e "  🟢 Сервіс Ollama активний на порту 11434"
    if curl -s http://127.0.0.1:11434/api/tags | grep -q "qwen2.5-coder"; then
        echo -e "  🟢 Модель сімейства ${GREEN}qwen2.5-coder${NC} присутня в Ollama"
    else
        echo -e "  ${YELLOW}⚠️ Рекомендована модель qwen2.5-coder:1.5b не знайдена.${NC}"
        echo -e "  👉 Завантажте її командою: ${GREEN}ollama pull qwen2.5-coder:1.5b${NC}"
    fi
else
    echo -e "  ${YELLOW}🟡 Ollama не запущена на 127.0.0.1:11434.${NC}"
    echo -e "  👉 Встановіть через: ${GREEN}curl -fsSL https://ollama.com/install.sh | sh${NC}"
fi

# 4. Перевірка файлу ключів ~/.env
echo -e "\n${BLUE}[4/6] Перевірка облікових записів та ключів (~/.env)...${NC}"
ENV_FILE="${HOME}/.env"
if [ -f "${ENV_FILE}" ]; then
    echo -e "  🟢 Файл конфігурації знайдено: ${GREEN}${ENV_FILE}${NC}"
    if grep -q "GEMINI_API_KEY" "${ENV_FILE}" 2>/dev/null; then
        echo -e "  🟢 ${GREEN}GEMINI_API_KEY${NC} (Google AI Pro) налаштовано"
    else
        echo -e "  ${YELLOW}⚠️ GEMINI_API_KEY не знайдено в ~/.env (наполегливо рекомендовано підключити Google AI Pro)${NC}"
    fi
    if grep -q "GROQ_API_KEY" "${ENV_FILE}" 2>/dev/null; then
        echo -e "  🟢 ${GREEN}GROQ_API_KEY${NC} (Groq Cloud LPU) налаштовано"
    else
        echo -e "  ${YELLOW}⚠️ GROQ_API_KEY не знайдено в ~/.env (безкоштовний LPU-інференс 14 400 RPD)${NC}"
    fi
else
    echo -e "  ${YELLOW}🟡 Файл ~/.env відсутній.${NC}"
    echo -e "  👉 Скопіюйте шаблон та додайте ваші ключі:"
    echo -e "     cp .env.example ~/.env && chmod 600 ~/.env"
    echo -e "     nano ~/.env"
fi

# 5. Бойова перевірка інференсу агентів
echo -e "\n${BLUE}[5/6] Запуск бойової перевірки інференсу ШІ (Tier 1 & Tier 2)...${NC}"
python3 core/engine/diagnostic_runner.py --check-agents

# 6. Валідація політики регламенту (34 структурні правила)
echo -e "\n${BLUE}[6/6] Запуск системного валідатора Генеральної політики...${NC}"
python3 core/verify/validate_general_policy.py

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}✅ Валідація завершена успішно! Середовище готове до розробки.${NC}"
echo -e "${GREEN}======================================================================${NC}"
