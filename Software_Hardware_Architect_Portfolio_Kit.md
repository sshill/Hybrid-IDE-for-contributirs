# Software-Hardware Architect Portfolio Kit: Cyber-Physical & Multi-Tier AI Systems
**Target Roles:** Senior / Principal Software Architect, Principal Systems Architect – Hardware Systems, Cyber-Physical Systems Architect, AI Systems & Platform Architect, Low-Latency Platform Architect  
**Candidate:** Serhii Khylevych (Principal Systems Architect)  
**Primary Repositories:**  
- **Track 1 (Cyber-Physical):** `https://github.com/sshill/fallaut4-STDFUA`  
  - Direct ICD Spec: `https://github.com/sshill/fallaut4-STDFUA/blob/main/proto/telemetry_bus.proto`  
  - Bioengineering Whitepaper (PDF): `https://github.com/sshill/fallaut4-STDFUA/blob/main/Bioengineering_Work_Example_Serhii_Khylevych.pdf`  
- **Track 2 (Multi-Tier AI Systems):** `https://github.com/sshill/Hybrid-IDE-for-contributirs`  
  - Direct Framework Repository: `https://github.com/sshill/Hybrid-IDE-for-contributirs`  
  - Architecture & Benchmark Spec: `https://github.com/sshill/Hybrid-IDE-for-contributirs/blob/main/README.md`  
  - Knowledge & Benchmarks: `docs/architecture/architect_benchmarks_and_tax_models.md`  

---

## 1. Quick Form Fields (Швидкі поля для веб-форм вакансій)

### Track 1: Cyber-Physical Telemetry Platform
- **Project Title:** Autonomous Multimodal Cyber-Physical Telemetry Platform & Digital Therapeutics Stand
- **GitHub / Portfolio URL:** `https://github.com/sshill/fallaut4-STDFUA`
- **One-line Tagline (< 140 chars):** Deterministic 1-ms multimodal cyber-physical telemetry complex with C LD_PRELOAD interceptors, Linux evdev 250Hz, & Protobuf ICD.
- **Short Summary (~300 chars):** Architected an autonomous cyber-physical telemetry platform integrating sub-millisecond ECG (Polar H10 BLE GATT), metabolic sensing (CGM ADB/Wi-Fi), and 250Hz motorics (Linux evdev/uinput) via a 1-ms deterministic bus (CLOCK_MONOTONIC_RAW) governed by a formal Protocol Buffers v3 ICD and HIL CI testing.

### Track 2: Multi-Tier AI Systems Architecture Platform
- **Project Title:** Autonomous Multi-Tier AI Agentic Platform & Deterministic Runtime Governance Stand
- **GitHub / Portfolio URL:** `https://github.com/sshill/Hybrid-IDE-for-contributirs`
- **One-line Tagline (< 140 chars):** Multi-tier hybrid edge/cloud AI architecture with RouteLLM SLA, FrugalGPT cascade, LiteLLM safe budgeting, & kernel pre-tool hard gates.
- **Short Summary (~300 chars):** Designed a 5-tier hybrid AI architecture orchestrating air-gapped local CPU edge models (Ollama <=7B) and cloud LPUs (Groq 120B @ 460 tok/s). Enforces deterministic execution via C/Python pre-tool interception gates, SLSA-grade provenance ledgers, and automated 34-point formal policy verification.

---

## 2. Standard ATS Long Answers (Розгорнуті відповіді для Greenhouse / Lever / Workday)

### Option A: Cyber-Physical / Hardware Systems / MilTech / Robotics
```text
Project: Autonomous Multimodal Cyber-Physical Telemetry Platform (GitHub: https://github.com/sshill/fallaut4-STDFUA)

Architected and deployed an end-to-end, deterministic cyber-physical research and digital therapeutics platform running under Linux Debian. The system captures and synchronizes heterogeneous biological, biomechanical, and simulation telemetry within a strict 1-millisecond master synchronization window (CLOCK_MONOTONIC_RAW).

Key Architectural Highlights:
1. Low-Level Kernel & Driver Layer: Engineered a custom C dynamic linking hook (hide_hidraw.c via LD_PRELOAD) to isolate raw USB endpoints and prevent user-space deadlocks; implemented zero-overhead Linux evdev/uinput event parsing (footpad_mapper.py) polling multi-axis controller inputs at 250 Hz (4-ms quantum) with aim tremor FFT filtering (8–12 Hz).
2. Multimodal Sensor Telemetry: Unified asynchronous streams across BLE GATT (Polar H10 ECG, 0.976 ms RR-intervals, real-time RMSSD / Baevsky stress index), reverse-engineered Android ADB/Wi-Fi continuous glucose data (LinX CGM), and multi-channel USB HID foot-switches.
3. Formal Contract Design & Quality Assurance: Formulated an exhaustive Interface Control Document (ICD) via Protocol Buffers v3 (proto/telemetry_bus.proto) and built a headless Hardware-in-the-Loop (HIL) emulation harness (mock_hardware_feeder.py) integrated into automated GitHub Actions CI.
```

### Option B: AI Systems / LLMOps / Principal Platform Architect
```text
Project: Autonomous Multi-Tier AI Systems Platform & Deterministic Governance Stand (GitHub: https://github.com/sshill/Hybrid-IDE-for-contributirs)

Architected a resilient 5-tier hybrid AI execution pipeline designed to eliminate agentic non-determinism, LLM policy bypasses, and token budget exhaustion on resource-constrained host hardware (Intel Core 3 100U, 16 GB RAM).

Key Architectural Highlights:
1. Hardware-Software Co-Design & Dynamic Routing: Engineered RouteLLM dynamic dispatch balancing SLA (30.0s) and throughput between an air-gapped local edge model (Ollama 1.5B @ 20 tok/s for AST checks) and Groq Cloud LPU (openai/gpt-oss-120b @ 460 tok/s for complex generation). Configured LiteLLM Safe Budgeting (-20% margin: 6400 TPM, 3200 max tokens) and an automated FrugalGPT failover cascade.
2. Deterministic Runtime Hard Gates: Replaced fragile prompt-based policies with kernel-level interception hooks (pre_tool_hook.py) physically preventing ad-hoc script injections (Zero Inline-Eval Gate) and enforcing SLSA-grade cryptographic SHA256 script provenance verification before execution.
3. Contract Governance & Automated Policy Verification: Enforced a strict 5-phase lifecycle (Diagnosis -> Plan -> Gate -> Execution -> Verification) with zero repeat network queries via Git-cached knowledge indexing and a formal test suite (34/34 structural markers passing in 0.0s). Assessed at 93.3% architectural maturity by Tier 4 Claude Sonnet Arbiter.
```

---

## 3. Resume / CV Experience Blocks (Блоки для резюме)

### Block 1: Cyber-Physical & Low-Latency Systems
```markdown
* **Autonomous Multimodal Cyber-Physical Telemetry Complex** | [GitHub: sshill/fallaut4-STDFUA](https://github.com/sshill/fallaut4-STDFUA)
  - Designed an end-to-end deterministic telemetry and stimulus platform under Linux Debian, integrating high-frequency physiological sensors with virtual cognitive workloads.
  - Built low-level C LD_PRELOAD system call interceptors (`hide_hidraw.c`) and custom Linux `evdev` / `uinput` kernel-level input processing engines operating at 250 Hz with < 20 µs ingestion latency.
  - Specified a formal binary Interface Control Document (ICD) using Protocol Buffers v3 (`telemetry_bus.proto`) mapping sub-millisecond cardiac (Polar H10 BLE GATT), metabolic (LinX CGM), and biomechanical telemetry.
  - Established a 1-ms deterministic timebase utilizing `CLOCK_MONOTONIC_RAW` and authored a headless Hardware-in-the-Loop (HIL) emulation harness verified via GitHub Actions CI/CD pipelines.
```

### Block 2: Multi-Tier AI Systems & Governance Platform
```markdown
* **Autonomous Multi-Tier AI Systems Architecture Platform** | [GitHub: sshill/Hybrid-IDE-for-contributirs](https://github.com/sshill/Hybrid-IDE-for-contributirs)
  - Architected a 5-tier hybrid AI orchestration engine coordinating air-gapped local CPU models (Ollama <=7B) and ultra-high-speed cloud LPUs (Groq 120B @ 460 tok/s) under strict 16 GB RAM bounds.
  - Developed RouteLLM throughput/SLA dynamic router with FrugalGPT failover cascades and LiteLLM safe buffer controls (6400 TPM, -20% headroom).
  - Built physical pre-execution interception gates (`pre_tool_hook.py`) and a cryptographic SHA256 provenance ledger, completely eliminating LLM script injection and inline evaluation anti-patterns.
  - Implemented automated 34-point architectural policy test harness and formal knowledge-caching protocol; independently evaluated at 93.3% maturity benchmark (Tier 4 Claude Sonnet Arbiter).
```

---

## 4. Cover Letter Paragraphs (Абзаци для супровідного листа)

### For Cyber-Physical / Robotics / Telecom / MilTech (e.g. Nokia, Aero Center):
```text
To demonstrate my hands-on architectural rigor in bridging low-latency software with physical hardware, I invite you to examine my open-source cyber-physical telemetry complex (https://github.com/sshill/fallaut4-STDFUA). In this project, I architected a deterministic 1-ms telemetry platform under Linux Debian that integrates multimodal sensors (sub-millisecond Polar H10 BLE ECG, LinX CGM, and 250Hz DualShock/USB-HID motorics) with a virtual cognitive stress engine. The system features low-level C LD_PRELOAD hooks for kernel device arbitration, a formal Protocol Buffers v3 Interface Control Document (ICD), and an automated headless Hardware-in-the-Loop (HIL) CI verification harness. This case study illustrates my end-to-end approach to hardware-software co-design, deterministic bus timing, and resilient systems architecture.
```

### For Platform / AI Systems / Enterprise Architect (e.g. N-iX, GlobalLogic):
```text
In addition to low-latency cyber-physical systems, I have architected and open-sourced an enterprise-grade Multi-Tier AI Systems Platform (https://github.com/sshill/Hybrid-IDE-for-contributirs). Facing the inherent non-determinism and policy bypass vulnerabilities of LLM-based agentic workflows, I engineered a hybrid local-edge/cloud architecture featuring dynamic RouteLLM SLA dispatch (balancing local CPU Ollama models with Groq LPU 120B @ 460 tok/s), LiteLLM Safe Budgeting, and FrugalGPT failover cascades. To guarantee zero-bypass policy compliance, I replaced declarative prompting with kernel-level pre-tool execution filters and SLSA-compliant SHA256 provenance tracking, backed by an automated 34-rule test suite. This demonstrates my capability to deliver production-grade, mathematically bounded AI systems architecture.
```

---

## 5. ATS Keyword Cloud (Хмара ключових слів для пошукових фільтрів)

```text
Software-Hardware Architecture, Systems Engineering, Linux Kernel, evdev, uinput, ioctl, C (LD_PRELOAD), Deterministic Telemetry, CLOCK_MONOTONIC_RAW, Interface Control Document (ICD), Protocol Buffers (Proto3), BLE GATT, Reverse-Engineering, ADB, Hardware-in-the-Loop (HIL), CI/CD, GitHub Actions, Mesa Vulkan 1.3, Sub-millisecond Latency, Multimodal Sensors, Digital Therapeutics (DTx), Multi-Tier AI Architecture, RouteLLM, FrugalGPT, LiteLLM, Groq LPU, Ollama, Agentic Governance, SLSA Provenance, Pre-Tool Hard Gates, Systemic Verification.
```

---

## 6. Compensation & Tax Reference (6,500 Gross $\to$ Net Reference)

- **Target Benchmark:** **6,500 EUR Gross $\implies \ge 5,000$ EUR Net Guaranteed**.
- **КЗпП (19.5% – 23.0%):** 5,005 – 5,232 EUR Net (227,700 – 238,000 UAH). Employer SSC capped at 26,400 UAH/mo (~580 EUR); Total Cost to Company $\approx$ 7,080 EUR/mo.
- **Diia.City Gig-Contract (6.5% – 10.0%):** 5,850 – 6,077 EUR Net (266,000 – 276,500 UAH).
- **FOP 3rd Group (6.0%):** 6,071 EUR Net (276,200 UAH).
