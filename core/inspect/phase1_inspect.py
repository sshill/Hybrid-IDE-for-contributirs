#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Фаза 1: Універсальний інспектор форматів та AST без запуску інтерпретатора.
Шлях: /home/hills/Documents/Antigravity_Mgr/tools/phase1_inspect.py
Стандарт: Zero-Dependency Python 3.13 Stdlib (ast, zipfile, xml.etree, json).
Усуває "інструментальний вакуум" для .docx, .xml, .json, .py AST.
"""

import argparse
import ast
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

sys.dont_write_bytecode = True

def inspect_ast(file_path: str) -> int:
    """Аналіз синтаксичного дерева файлу Python без виконання коду."""
    if not os.path.exists(file_path):
        print(f"❌ Файл не знайдено: {file_path}", file=sys.stderr)
        return 1
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code, filename=file_path)
    except SyntaxError as e:
        print(f"❌ Помилка синтаксису Python у {file_path}: {e}", file=sys.stderr)
        return 2

    print(f"\n📂 AST-Аналіз файлу: {file_path}")
    print("=" * 60)

    imports = []
    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for n in node.names:
                imports.append(f"{mod}.{n.name}")
        elif isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append((node.name, methods, node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            functions.append((node.name, args, node.lineno))

    if imports:
        print(f"📦 Імпорти ({len(imports)}): {', '.join(imports)}")
    if classes:
        print(f"\n🏛️ Класи ({len(classes)}):")
        for name, methods, line in classes:
            print(f"  • class {name} (рядок {line}): методи -> {', '.join(methods) if methods else 'немає'}")
    if functions:
        print(f"\n⚙️ Функції ({len(functions)}):")
        for name, args, line in functions:
            print(f"  • def {name}({', '.join(args)}) (рядок {line})")

    print(f"\n📊 Всього рядків AST: {len(tree.body)} кореневих вузлів.")
    return 0

def inspect_docx(file_path: str, show_comments: bool = True) -> int:
    """Безпечний парсинг вмісту та коментарів DOCX без Microsoft Word / LibreOffice."""
    if not os.path.exists(file_path):
        print(f"❌ Файл не знайдено: {file_path}", file=sys.stderr)
        return 1

    try:
        with zipfile.ZipFile(file_path, "r") as z:
            file_names = z.namelist()
            print(f"\n📄 DOCX Інспекція: {file_path}")
            print("=" * 60)

            # 1. Читання головного тексту
            if "word/document.xml" in file_names:
                xml_data = z.read("word/document.xml")
                root = ET.fromstring(xml_data)
                # Вилучення тексту з w:t
                paragraphs = []
                for p in root.iter():
                    if p.tag.endswith("}p"):
                        texts = [t.text for t in p.iter() if t.tag.endswith("}t") and t.text]
                        if texts:
                            paragraphs.append("".join(texts))

                print(f"📑 Загальна кількість абзаців: {len(paragraphs)}")
                print("Перші 5 абзаців:")
                for i, p in enumerate(paragraphs[:5], 1):
                    print(f"  [{i}] {p[:120]}{'...' if len(p) > 120 else ''}")

            # 2. Читання коментарів
            if show_comments and "word/comments.xml" in file_names:
                comm_data = z.read("word/comments.xml")
                comm_root = ET.fromstring(comm_data)
                print(f"\n💬 Знайдені коментарі (word/comments.xml):")
                count = 0
                for c in comm_root.iter():
                    if c.tag.endswith("}comment"):
                        author = c.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author", "Невідомий")
                        date = c.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}date", "")
                        texts = [t.text for t in c.iter() if t.tag.endswith("}t") and t.text]
                        comm_text = "".join(texts).strip()
                        print(f"  • Автор: {author} [{date}]: \"{comm_text}\"")
                        count += 1
                if count == 0:
                    print("  (Коментарів не виявлено)")
        return 0
    except Exception as e:
        print(f"❌ Помилка інспекції DOCX {file_path}: {e}", file=sys.stderr)
        return 3

def inspect_xml(file_path: str) -> int:
    """Безпечний парсинг XML файлу без ризику entity expansion."""
    if not os.path.exists(file_path):
        print(f"❌ Файл не знайдено: {file_path}", file=sys.stderr)
        return 1
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        print(f"\n🌐 XML Інспекція: {file_path}")
        print("=" * 60)
        print(f"Кореневий тег: <{root.tag}> | Атрибути: {root.attrib}")
        children = list(root)
        print(f"Кількість дочірніх вузлів першого рівня: {len(children)}")
        for i, child in enumerate(children[:8], 1):
            sub_count = len(list(child))
            print(f"  [{i}] <{child.tag}> {child.attrib} (підвузлів: {sub_count})")
        return 0
    except Exception as e:
        print(f"❌ Помилка парсингу XML: {e}", file=sys.stderr)
        return 2

def inspect_json(file_path: str) -> int:
    """Структурний аналіз JSON файлу: типи даних, розмірності та ключі."""
    if not os.path.exists(file_path):
        print(f"❌ Файл не знайдено: {file_path}", file=sys.stderr)
        return 1
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"\n📋 JSON Інспекція: {file_path}")
        print("=" * 60)
        if isinstance(data, dict):
            print(f"Тип кореня: Object/Dict ({len(data)} ключів)")
            for k, v in list(data.items())[:12]:
                val_type = type(v).__name__
                if isinstance(v, list):
                    info = f"Array[{len(v)}]"
                elif isinstance(v, dict):
                    info = f"Dict[{len(v)} keys]"
                else:
                    info = str(v)[:60]
                print(f"  • \"{k}\": {val_type} -> {info}")
        elif isinstance(data, list):
            print(f"Тип кореня: Array/List ({len(data)} елементів)")
            if data:
                print(f"  Приклад елемента [0]: {type(data[0]).__name__}")
        return 0
    except Exception as e:
        print(f"❌ Помилка читання JSON: {e}", file=sys.stderr)
        return 2

def inspect_telemetry(session_query: str = "") -> int:
    """Динамічний 2D-аналіз контексту сесії: кроки, розмір транскрипту, токени Nin/Nout та статус компакції."""
    brain_base = "/home/hills/.gemini/antigravity/brain"
    target_dir = ""

    if session_query and session_query != "current":
        if os.path.isabs(session_query) and os.path.isdir(session_query):
            target_dir = session_query
        else:
            cand = os.path.join(brain_base, session_query)
            if os.path.isdir(cand):
                target_dir = cand
            else:
                matches = [p for p in os.listdir(brain_base) if session_query in p]
                if matches:
                    target_dir = os.path.join(brain_base, matches[0])

    if not target_dir and os.path.exists(brain_base):
        cand_dirs = []
        for d in os.listdir(brain_base):
            d_path = os.path.join(brain_base, d)
            if os.path.isdir(d_path):
                t_file = os.path.join(d_path, ".system_generated", "logs", "transcript.jsonl")
                if os.path.isfile(t_file):
                    cand_dirs.append((os.path.getmtime(t_file), d_path))
                else:
                    cand_dirs.append((os.path.getmtime(d_path), d_path))
        if cand_dirs:
            cand_dirs.sort(key=lambda x: x[0], reverse=True)
            target_dir = cand_dirs[0][1]

    if not target_dir or not os.path.exists(target_dir):
        print("❌ Не вдалося знайти активну сесію для зняття телеметрії.", file=sys.stderr)
        return 1

    log_file = os.path.join(target_dir, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(log_file):
        print(f"❌ Файл транскрипту не знайдено: {log_file}", file=sys.stderr)
        return 1

    steps_count = 0
    max_step_index = -1
    line_count = 0
    file_bytes = os.path.getsize(log_file)
    last_user_len = 0
    last_model_len = 0
    has_summary = False

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    data = json.loads(line)
                    t_type = data.get("type", "")
                    source = data.get("source", "")
                    content = str(data.get("content", ""))

                    # Визначення кроку з числового step_index
                    s_idx = data.get("step_index")
                    if s_idx is None:
                        s_idx = data.get("stepIdx")
                    if s_idx is not None:
                        try:
                            max_step_index = max(max_step_index, int(s_idx))
                        except (ValueError, TypeError):
                            pass

                    # Усунення хибного спрацьовування на підрядок <CONTEXT_SUMMARY>
                    # Тільки системні повідомлення або тип компакції вважаються реальною компакцією
                    is_system = source in ("SYSTEM", "SYSTEM_SDK")
                    is_compaction_type = t_type in ("CONTEXT_COMPACTION", "COMPACTED_SUMMARY")
                    is_standalone_tag = (
                        content.strip().startswith("<CONTEXT_SUMMARY>") and
                        source not in ("MODEL", "USER_EXPLICIT") and
                        t_type not in ("GENERIC", "USER_INPUT", "PLANNER_RESPONSE")
                    )
                    if "<CONTEXT_SUMMARY>" in content and (is_system or is_compaction_type or is_standalone_tag):
                        has_summary = True

                    if t_type == "USER_INPUT":
                        last_user_len = len(content)
                    elif t_type in ("PLANNER_RESPONSE", "MODEL"):
                        last_model_len = len(content)
                except Exception:
                    pass
    except Exception as e:
        print(f"❌ Помилка читання транскрипту: {e}", file=sys.stderr)
        return 2

    if max_step_index >= 0:
        steps_count = max(line_count, max_step_index + 1)
    else:
        steps_count = line_count

    # Оцінка токенів (1 токен ≈ 4 символи)
    est_cumulative_tokens = file_bytes // 4
    est_nin = max(350, (last_user_len // 4) + 1200)
    est_nout = max(150, last_model_len // 4)

    if steps_count > 800 or est_cumulative_tokens > 160000 or has_summary:
        zone = "🔴 ЗОНА 3: ГЛИБОКА СЕСІЯ"
        action = "Вичерпання лімітів! Обов'язкова фіксація в Git та перехід на /bridge."
    elif steps_count > 600 or est_nin > 3000 or est_cumulative_tokens > 80000:
        zone = "🟡 ЗОНА 2: НАСИЧЕНА"
        action = "Підвищена щільність! Пріоритет локальних Git-комітів, лаконічність звітів."
    else:
        zone = "🟢 ЗОНА 1: ОПТИМАЛЬНА"
        action = "Штатна робота за 5-фазним регламентом."

    session_id = os.path.basename(target_dir)
    sess_short = session_id[:8]

    # Запис атестаційного прапорця успішного виміру телеметрії (Telemetry Gate v0.9.8)
    try:
        telemetry_meta = {
            "session_id": session_id,
            "timestamp": time.time(),
            "steps": steps_count,
            "zone": zone,
            "cumulative_tokens": est_cumulative_tokens,
            "nin": est_nin,
            "nout": est_nout
        }
        for flag_path in (
            f"/tmp/antigravity_telemetry_{sess_short}.flag",
            f"/tmp/antigravity_telemetry_{session_id}.flag",
            "/tmp/antigravity_telemetry_inspected.flag"
        ):
            with open(flag_path, "w", encoding="utf-8") as tf:
                json.dump(telemetry_meta, tf)
    except Exception:
        pass

    print("┌────────────────────────────────────────────────────────────────────────┐")
    print("│ 📊 [CONTEXT HEALTH & DYNAMIC TELEMETRY INDICATOR]                      │")
    print("├────────────────────────────────────────────────────────────────────────┤")
    print(f"│ • Сесія / ID         : {session_id[:16]}... ({session_id})")
    print(f"│ • Індикатор / Зона   : {zone}")
    print(f"│ • Кроки сесії (S)    : {steps_count} / 800 кроків")
    print(f"│ • Обсяг транскрипту  : {file_bytes / (1024*1024):.2f} MB (~{est_cumulative_tokens // 1000}k tok)")
    print(f"│ • Останній запит     : Nin: ~{est_nin} tok | Nout: ~{est_nout} tok")
    print(f"│ • Контекст-компакція : {'⚠️ Активовано (<CONTEXT_SUMMARY>)' if has_summary else '🟢 Норма (без стиснення)'}")
    print(f"│ • Рекомендація       : {action}")
    print("└────────────────────────────────────────────────────────────────────────┘")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Phase 1 Zero-Dep Format & AST Inspector (Antigravity_Mgr)")
    parser.add_argument("--ast", type=str, help="Аналіз Python AST файлу")
    parser.add_argument("--docx", type=str, help="Інспекція .docx документа та коментарів")
    parser.add_argument("--xml", type=str, help="Безпечна інспекція .xml файлу")
    parser.add_argument("--json", type=str, help="Структурна інспекція .json файлу")
    parser.add_argument("--telemetry", nargs="?", const="current", default=None, help="Динамічна телеметрія контексту сесії (кроки, токени Nin/Nout)")

    args = parser.parse_args()

    if args.telemetry is not None:
        return inspect_telemetry(args.telemetry)
    elif args.ast:
        return inspect_ast(args.ast)
    elif args.docx:
        return inspect_docx(args.docx)
    elif args.xml:
        return inspect_xml(args.xml)
    elif args.json:
        return inspect_json(args.json)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
