# ENCLAVE_INTERFACE.md
**Hybrid IDE Enclave Architecture – v0.9.12**  
Reference guide for command‑line interface (CLI) options and HTTP service endpoints.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)  
2. [Enclave Lifecycle – 5 Phases](#enclave-lifecycle---5-phases)  
3. [CLI Options](#cli-options)  
4. [HTTP Endpoints](#http-endpoints)  
5. [Example Invocations](#example-invocations)  
6. [Version & Compatibility](#version--compatibility)  

---

## Architecture Overview
The Hybrid IDE Enclave isolates untrusted code execution while providing deterministic, auditable results. Interaction occurs through:

* **CLI** – for local automation, CI pipelines, and developer tooling.  
* **HTTP API** – for remote orchestration, monitoring, and integration with external services.

Both interfaces share a common **state machine** that progresses through five well‑defined phases.

---

## Enclave Lifecycle – 5 Phases
| Phase | Symbolic Name | Trigger | Core Responsibilities | Typical Outputs |
|-------|---------------|---------|-----------------------|-----------------|
| **1** | **Initialize** | `enclave start` or HTTP `POST /apply` (first call) | • Load configuration<br>• Verify runtime dependencies<br>• Allocate secure memory | `init‑token`, environment snapshot |
| **2** | **Validate** | Automatic after Init | • Perform static analysis<br>• Run `--check-all` policies<br>• Verify cryptographic signatures | Validation report, `validation‑hash` |
| **3** | **Execute** | After successful Validate | • Run user‑provided payload in sandbox<br>• Emit telemetry (`--telemetry`)<br>• Optionally run battle‑test (`--battle-test`) | Execution log, result payload |
| **4** | **Attest** | After Execute (or on explicit request) | • Generate attestation evidence<br>• Sign with enclave key (`--attest-arbiter`)<br>• Build verification chain (`--verify-chain`) | Attestation bundle, `attestation‑token` |
| **5** | **Cleanup** | End of session or error | • Zero out memory<br>• Revoke temporary keys<br>• Emit final health status | `shutdown‑report` |

> **Note:** Phases can be short‑circuited by failures; the enclave will transition directly to **Cleanup** while emitting error diagnostics.

---

## CLI Options
| Option | Category | Description | Example |
|--------|----------|-------------|---------|
| `--battle-test` | Execution | Runs a deterministic “battle‑test” workload before the main payload to stress‑test resource limits. | `enclave run --battle-test` |
| `--telemetry` | Execution | Streams real‑time telemetry (CPU, memory, I/O) to stdout or a configured endpoint. | `enclave run --telemetry` |
| `--check-all` | Validation | Enables exhaustive static and dynamic checks (lint, dependency audit, policy compliance). | `enclave validate --check-all` |
| `--help-tools` | General | Prints extended help for auxiliary tools (`arbiter`, `verifier`, `monitor`). | `enclave --help-tools` |
| `--query <expr>` | Query | Executes a JMESPath‑compatible query against the enclave’s current state. | `enclave query --query "tasks[?status=='failed']"` |
| `--target <uri>` | General | Overrides the default enclave service URI (e.g., `http://localhost:8080`). | `enclave apply --target https://api.example.com/enclave` |
| `--attest-arbiter <verdict>` | Attestation | Реєстрація вердикту арбітра Antigravity Pool (PASS). | `enclave --attest-arbiter PASS` |
| `--probe-providers` | Diagnostics | Зонди авторизації/квот (Ollama, Groq, Gemini, OpenAI, OpenRouter, Copilot). | `enclave --probe-providers` |
| `--provider <name>` | Diagnostics | Опитування конкретного провайдера (`gemini`, `openai`, `ollama` тощо). | `enclave --probe-providers --provider gemini` |
| `--verify-chain` | Attestation | Верифікація ланцюга HMAC-паспортів у леджері. | `enclave --verify-chain` |
| `--help` | General | Стандартна довідка параметрів. | `enclave --help` |

## HTTP Endpoints
- `GET /probe-providers` – діагностичні зонди авторизації та квот провайдерів ШІ.
- `GET /battle-test` – 4-Tier AI Battle Test (Ollama, Groq, Claude Sonnet, Copilot probe).
- `GET /telemetry` – 2D-телеметрія активної сесії.
- `GET /verify-chain` – детерміністична перевірка ланцюга HMAC-паспортів леджера.
- `POST /apply` – атомарний синтез/патч із первинним контролем та випуском паспорта.
- `POST /query` – суверенний шлюз ШІ з Failover (Copilot -> Gemini 1M/2M -> Claude).
- `POST /attest` – фіксація вердикту арбітра Antigravity Pool.

