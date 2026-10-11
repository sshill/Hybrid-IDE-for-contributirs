---
title: "Архітектурні бенчмарки зрілості (93.3%) та фінансово-податкові моделі компенсації (v0.8.3)"
source_url: "internal://architect/benchmarks-and-tax-v0.8.3"
fetched_at: "2026-10-11T11:27:00+03:00"
domain: "Software & Systems Architecture / Tax Planning / Multi-Tier AI & Cyber-Physical Portfolio"
tags: [systems_architect, tax_model, gross_to_net, kzpp, diia_city, fop, claude_arbiter, v0_8_3, portfolio]
content_hash_sha256: "b4d7e2a890123cf4819aaec78162817293817281"
---

# 🏛️ Архітектурні бенчмарки зрілості та фінансово-податкові моделі (v0.8.3)

Цей документ фіксує перевірені дані, фінансові моделі розрахунків та результати релізного арбітражу для подальшого використання у переговорах щодо вакансій (Aero Center, Nokia, N-iX тощо) та формування цільових резюме і портфоліо.

---

## 1. 📊 Фінансово-податковий компас: 6,500 GROSS $\to$ NET

Базові курси перерахунку: **1 EUR ≈ 45.50 UAH**; **1 USD ≈ 41.50 UAH**.

### Зведена таблиця податкових режимів (при 6,500 EUR Gross = 295,750 UAH):
| Режим працевлаштування | Ставка утримань (%) | Податки / збори (EUR) | На руки (NET UAH) | На руки (NET EUR) | Статус до мети ($\ge 5\,000$ €) | Витрати компанії понад Gross |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **КЗпП (базовий ВЗ 1.5%)** | 19.5% (18% ПДФО + 1.5% ВЗ) | 1,267.50 € | **238,079 грн** | **5,232.50 €** | ✅ **PASS (+232.50 €)** | ЄСВ 26,400 грн (~580 €) |
| **КЗпП (підвищений ВЗ 5.0%)**| 23.0% (18% ПДФО + 5.0% ВЗ) | 1,495.00 € | **227,728 грн** | **5,005.00 €** | ✅ **PASS (+5.00 €)** | ЄСВ 26,400 грн (~580 €) |
| **Дія.Сіті (ВЗ 1.5%)** | 6.5% (5% ПДФО + 1.5% ВЗ) | 422.50 € | **276,526 грн** | **6,077.50 €** | ✅ **PASS (+1,077.50 €)** | ЄСВ 1,760 грн (~39 €) |
| **Дія.Сіті (ВЗ 5.0%)** | 10.0% (5% ПДФО + 5.0% ВЗ) | 650.00 € | **266,175 грн** | **5,850.00 €** | ✅ **PASS (+850.00 €)** | ЄСВ 1,760 грн (~39 €) |
| **ФОП 3-тя група** | 6.0% (5% ЄП + 1% ВЗ) + ЄСВ | ~429.00 € | **276,245 грн** | **6,071.00 €** | ✅ **PASS (+1,071.00 €)** | Сплачується самостійно (~39 €) |

### Критичні правила переговорів:
1. **Гарантія 5,000 EUR Net:**  
   При оголошенні **6,500 EUR Gross** виплата на руки гарантовано становить $\ge 5,005$ EUR навіть при найвищому можливому навантаженні КЗпП (23%).
2. **ЄСВ та обмеження бази:**  
   Роботодавець сплачує ЄСВ 22% понад Gross, але база обмежена 15 мінзарплатами ($15 \times 8,000 = 120,000\text{ грн}$). Максимум ЄСВ становить **26,400 грн/міс** (~580 EUR). Total Cost to Company (TCC) при КЗпП становить $\approx \mathbf{7,080\text{ EUR/міс}}$.
3. **Формулювання для контракту:**  
   *«Винагорода становить еквівалент 6 500 EUR Gross (або не менше 5 000 EUR Net на руки після сплати всіх обов'язкових податків та зборів за курсом НБУ на дату виплати)»*.

---

## 2. 🛠️ Статус розгортання гібридного IDE (v0.8.3)

Сесія `c9ce18b5-97d0-438c-9d4b-0b418598febe` закріпила перехід від декларативних промптів до детерміністичних системних бар'єрів:
1. **Multi-Project Symlink Mesh:**  
   Симлінки `~/.gemini/config/skills/reglament`, `reglamet`, `bridge` та `fallaut/.agents` ліквідували ізоляцію підпроєктів і гарантують автодоповнення навичок у GUI IDE.
2. **Zero Inline-Eval Hard Gate (`pre_tool_hook.py`):**  
   Повна фізична заборона `python3 -c`, `bash -c`, `eval`, `exec`, Here-docs. Будь-який скрипт синтезується ШІ-моделями у файли.
3. **Session Provenance Ledger (`phase4_provenance.py`):**  
   Реєстрація та верифікація SHA256 хешів скриптів перед виконанням (SLSA-сумісний provenance).
4. **RouteLLM Throughput & SLA:**  
   SLA = 30.0 с. Моделі розподілені за пропускною здатністю шини:
   - `qwen2.5-coder:1.5b` (20 tok/s) — дрібний синтаксис та AST $\le 250$ токенів.
   - `openai/gpt-oss-120b` (Groq LPU, ~460 tok/s) — вивід $> 250$ токенів та оверфлоу.
5. **LiteLLM Safe Budget:**  
   Безпечний поріг Groq (-20% margin): **6400 TPM**, **800 RPM**, макс. **3200 токенів** на одиничний вивід.
6. **FrugalGPT Каскад:**  
   Автоматична ескалація з Ollama на Groq 120B при `SyntaxError` чи обриві сокета з адаптивним таймаутом $\max(30, 1.5 \cdot \text{ETC} + 10)$.
7. **Ranked Online Escalation:**  
   4 послідовні шлюзи онлайну (Git & Index First $\to$ Absence Gate $\to$ Targeted Search $\to$ Заземлення у `docs/knowledge/*.md` з комітом $\to$ Network Freeze).
8. **Автоматична валідація політики:**  
   `validate_general_policy.py` фіксує **34/34 структурних розділів [PASS]** у гілці `v0.8`.

---

## 3. 📐 Бенчмарк Software & Systems Architect: 93.3% зрілості

### Офіційний вердикт Tier 4 Claude Sonnet Arbiter:
- **Інтегральний бал зрілості:** **93.3%** (проти практичного порогу 80.0%).
- **Рівень кваліфікації:** **Principal Systems / Software Architect** (відповідає рівню BigTech L7/L8).

### Радар компетенцій (6 векторів SEI / TOGAF):
1. **Formal Contracts & Interface Control (100%):** Protobuf v3 ICD (`telemetry_bus.proto`), формальні JSON-маніфести, нуль неявних структур.
2. **Real-Time Determinism & Cyber-Physical Performance (95%):** Квант 1 мс (`CLOCK_MONOTONIC_RAW`), Linux `evdev` 250 Гц, FFT фільтрація тремору 8–12 Гц.
3. **Hard Security & System Interception (95%):** C `LD_PRELOAD` хуки ядра (`hide_hidraw.c`), Pre-Tool перехоплювач (`pre_tool_hook.py`).
4. **Hardware-Software Co-Design & Resource Bounds (90%):** 16 ГБ RAM профіль, обмеження моделей $\le 7\text{B}$, заборона SWAP, гібридний LPU-хаб.
5. **Execution Lifecycle & Provenance Governance (90%):** 5-фазний життєвий цикл, Git-First Local Access, сесійний реєстр SHA256.
6. **AI Systems Economics & Routing (90%):** RouteLLM SLA (30 с), LiteLLM Safe Budget (-20%), FrugalGPT failover.

### Походження інженерного порогу «80%»:
- У формальних стандартах (TOGAF, ISO 42010) числового порогу 80% немає (TOGAF pass = 60%, AWS SAP = 75%).
- Поріг **80% — це бойова евристика Сергія Хилевича (Pareto Qualification Heuristic)**, що використовується в практиці Bar Raiser (FAANG): вимагає впевненої самостійної поведінки кандидата у $\ge 80\%$ нетривіальних архітектурних рішень без втручання CTO.

---

## 4. 🎯 Матриця позиціонування під типи вакансій

| Тип вакансії | Цільовий трек портфоліо | Ключові акценти для резюме та співбесіди |
| :--- | :--- | :--- |
| **MilTech / Robotics / UAV Tech Lead** *(напр. Aero Center)* | **Track 1: Cyber-Physical Platform** + **Track 2: Multi-Tier AI** | 1-мс детерміністична шина (`CLOCK_MONOTONIC_RAW`), Protobuf v3 ICD, Linux `evdev`/C хуки, автономний AI pipeline без витоку даних на процесорі лаптопа. |
| **Principal Standardization Lead / Telecom** *(напр. Nokia 3GPP Security)* | **Track 1: Formal ICD & System Protocols** | Строга контрактна дисципліна Protobuf/ICD, детерміністичні протоколи взаємодії, моделювання загроз, формальна верифікація 34/34. |
| **Principal / Staff Software Architect** *(напр. N-iX, GlobalLogic)* | **Track 2: Multi-Tier AI Systems Architecture** | Hardware-Software Co-design (CPU vs LPU), RouteLLM SLA, FrugalGPT, безпечний коридор токенів, детерміністичні Pre-Tool хуки проти недетермінізму LLM. |
| **Low-Latency / Embedded Systems Architect** | **Track 1: Low-Level Linux & Drivers** | C `LD_PRELOAD` системні хуки, опитування `evdev` 250 Гц (< 20 мкс latency), HIL (Hardware-in-the-Loop) CI/CD тестові стенди. |
