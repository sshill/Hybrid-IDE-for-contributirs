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

def main():
    parser = argparse.ArgumentParser(description="Phase 1 Zero-Dep Format & AST Inspector (Antigravity_Mgr)")
    parser.add_argument("--ast", type=str, help="Аналіз Python AST файлу")
    parser.add_argument("--docx", type=str, help="Інспекція .docx документа та коментарів")
    parser.add_argument("--xml", type=str, help="Безпечна інспекція .xml файлу")
    parser.add_argument("--json", type=str, help="Структурна інспекція .json файлу")

    args = parser.parse_args()

    if args.ast:
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
