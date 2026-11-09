# Контракт Довіреного Анклаву — v0.9.13

Цей документ описує наявний інтерфейс `core/enclave/enclave_daemon.py`,
а не гарантію виконання всіх фаз регламенту. `--help` показує CLI,
`--help-tools` і `GET /help` повертають JSON-довідку HTTP. CLI не має
підкоманд `enclave run`, `apply` або `query`.

Демон запускається командою `python3 core/enclave/enclave_daemon.py --daemon`.
Типова адреса — `127.0.0.1:8765`; `--host` і `--port` налаштовують її.
HTTP не реалізує автентифікацію: не відкривайте його недовіреним клієнтам.
Лише CLI `--target` делегує виклик доступному демону; інші CLI-операції
виконуються локально. При помилці виклику демона `--target` повторює операцію
локально; помилка відповіді не доводить, що демон не встиг змінити файл.

## Застосування коду: CLI `--target`, HTTP `POST /apply`

`--target` / `target_path` — шлях до **файлу**, не URL. `--task` /
`task_prompt` — завдання для генерації; `--direct-code` / `direct_code` —
готовий текст без звернення до моделі. При передачі обох використовується
`direct_code`, а `task_prompt` також використовується для Anti-Echo.
Без жодного з них операція повертає помилку.

| CLI | JSON | Значення |
|---|---|---|
| `--target` | `target_path` | Цільовий файл; HTTP також приймає `target_file`. |
| `--task` | `task_prompt` | Інструкція моделі; HTTP також приймає `task`. |
| `--direct-code` | `direct_code` | Код або фрагмент для заміни. |
| `--mode` | `mode` | Для `/apply`: `synthesize` (типово) або `patch`. |
| `--tier`, `--model` | `tier`, `model` | Необов'язкові налаштування маршрутизації моделі. |
| `--patch-target` | `patch_target` | Непорожній точний текст для заміни, обов'язковий у `patch`. |
| `--start-line`, `--end-line` | `start_line`, `end_line` | Необов'язковий діапазон: обидва номери, від 1, включно. |
| `--allow-multiple` | `allow_multiple` | Дозволити заміну **всіх** збігів у діапазоні або файлі; типово `false`. |
| — | `session_id` | Необов'язковий ідентифікатор сесії для паспорта. |

`synthesize` створює або перезаписує файл. `patch` потребує наявного файла
та шукає точний текст у заданому діапазоні або у всьому файлі. Без
`--allow-multiple` має бути рівно один збіг; за його відсутності або при
неоднозначності запис не відбувається. Для Python виконуються AST-перевірка,
симуляція і кроки паспорта перед атомарним записом. Помилка після запису,
зокрема підтвердження паспорта, не гарантує відсутності змін у файлі.
Завжди узгоджуйте ціль і вміст із затвердженим планом.

Приклади для санкціонованих тестових файлів:

```bash
python3 core/enclave/enclave_daemon.py --target /tmp/example.py \
  --direct-code 'print("hello")' --mode synthesize --json-output
python3 core/enclave/enclave_daemon.py --target /tmp/example.py \
  --mode patch --patch-target 'hello' --direct-code 'world' --json-output
```

Задавайте коректні номери рядків для конкретного файла. Якщо справді потрібна
заміна кількох збігів, додайте `--allow-multiple` після перевірки діапазону.
HTTP-еквівалент запиту:

```http
POST /apply
Content-Type: application/json

{"target_path":"/tmp/example.py","mode":"patch","patch_target":"hello","direct_code":"world","allow_multiple":false}
```

Успішний `/apply` повертає HTTP 200 та receipt зі `status: SUCCESS`, шляхом,
хешами й `passport_id`; помилка застосування — HTTP 422 та `status: ERROR`.
CLI з `--json-output` друкує receipt; код завершення 0 означає `SUCCESS`,
1 — помилку.

## Запити до моделі: CLI `--query` / `--query-file`, HTTP `POST /query`

Це текстові промпти моделі, **не JMESPath**. `--query-file` читає UTF-8 файл
як повний промпт, без автоматичного додавання інструкції аудиту; якщо
вказано також `--query`, використовується файл. Формулюйте задачу й критерії
перевірки у самому промпті. Не передавайте секрети.

```bash
python3 core/enclave/enclave_daemon.py \
  --query 'Перевір наведений план на пропущені ризики: ...' \
  --tier 4 --mode audit --json-output
python3 core/enclave/enclave_daemon.py \
  --query-file /tmp/audit-prompt.txt --tier 4 --mode precheck --json-output
```

```http
POST /query
Content-Type: application/json

{"prompt":"Перевір наведений план на пропущені ризики: ...","tier":4,"mode":"audit"}
```

HTTP приймає `prompt`, `tier`, `model`, `mode`; типові значення — tier 1 і
mode `query`. CLI має спільний `--mode` з типовим `synthesize`, тому для
аудиту чи precheck задавайте `--mode` явно. HTTP повертає 200 для `SUCCESS`,
422 для `ERROR`. CLI повертає 0 або 1 відповідно. `SUCCESS` означає лише,
що результат не починається з `ERROR:`: це **не доказ проведеного аудиту,
PASS чи незалежної перевірки**. Маршрутизація може повернути текст атестації
за наявності старого прапорця; перевіряйте зміст і походження відповіді.

## Інші операції

| CLI | HTTP | Дія |
|---|---|---|
| `--help-tools` | `GET /help`, `/help-tools` | JSON-довідка. |
| — | `GET /health` | Статус демона. |
| `--telemetry` | `GET /telemetry` | Телеметрія; за відсутності даних можливі типові значення. |
| `--battle-test` | `GET /battle-test` (`/battletest`) | Запити для перевірки провайдерів; потребують доступних сервісів. |
| `--probe-providers [--provider NAME]` | `GET /probe-providers` (`/probe_providers`) | Зондування провайдерів; HTTP не приймає фільтр провайдера. |
| `--check-all` | `GET /diagnostics` (`/check-all`) | Телеметрія і battle-test, не повний набір перевірок політики. |
| `--verify-chain` | `GET /verify-chain` (`/verify_chain`) | Перевірка ланцюга паспортів. |
| `--attest-arbiter [VERDICT]` | `POST /attest` | Запис прапорця атестації; не перевіряє самостійно поточний запит. |
| `--set-credential KEY VALUE [--project ID]` | Немає | Запис облікових даних через CLI; значення в аргументах може бути видимим іншим процесам або в історії команд. |

`--json-output` підтримується не всіма операціями; `--verify-chain` та
`--check-all` і так виводять JSON. Для `POST /attest` поля `verdict` та
`arbiter` необов'язкові. Атестація не прив'язана до хешу поточного запиту і
не є доказом його незалежного аудиту.
