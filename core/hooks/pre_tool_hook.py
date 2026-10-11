#!/usr/bin/env python3
import sys
import os
import re
import ast
import argparse
import traceback

# Prevent creation of .pyc files
sys.dont_write_bytecode = True

def load_file(path):
    """Read file content, raise informative error if fails."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Unable to read '{path}': {e}") from e

def write_file(path, content):
    """Write content back to file atomically."""
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception as e:
        # Cleanup temp file if something went wrong
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise RuntimeError(f"Unable to write updated content to '{path}': {e}") from e

def parse_trusted_prefixes(source):
    """
    Locate the assignment to ``trusted_host_prefixes`` and return its AST node
    together with the surrounding source slice.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise RuntimeError(f"Syntax error while parsing the hook file: {e}") from e

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "trusted_host_prefixes":
                    # Determine the exact source slice for this assignment
                    # ast nodes have lineno (1‑based) and end_lineno (Python 3.8+)
                    start = node.lineno - 1  # zero based index
                    end = getattr(node, "end_lineno", None)
                    if end is None:
                        # Fallback: find the next blank line after start
                        lines = source.splitlines()
                        end = start + 1
                        while end < len(lines) and lines[end].strip():
                            end += 1
                    else:
                        end = end  # already 1‑based inclusive
                    return (node, start, end)
    raise RuntimeError("Could not locate 'trusted_host_prefixes' assignment in the file.")

def format_prefix_list(prefixes, indent):
    """Return a nicely formatted Python list literal."""
    lines = ["["]
    for p in prefixes:
        lines.append(f"{indent}'{p}',")
    lines.append(f"{indent[:-4]}]")
    return "\n".join(lines)

def update_trusted_prefixes(content, new_prefixes):
    """
    Add ``new_prefixes`` to the existing ``trusted_host_prefixes`` list,
    preserving order and avoiding duplicates.
    """
    node, start_line, end_line = parse_trusted_prefixes(content)
    lines = content.splitlines()
    # Extract the original list literal source
    original_src = "\n".join(lines[start_line:end_line])
    # Evaluate the existing list safely (it should be a literal)
    try:
        existing = ast.literal_eval(original_src.split('=', 1)[1].strip())
        if not isinstance(existing, list):
            raise ValueError
    except Exception:
        raise RuntimeError("Existing 'trusted_host_prefixes' is not a simple list literal.")
    # Merge while preserving original order
    merged = existing[:]
    for p in new_prefixes:
        if p not in merged:
            merged.append(p)
    # Determine indentation (detect from the line containing the assignment)
    assign_line = lines[start_line]
    indent_match = re.match(r"(\s*)trusted_host_prefixes\s*=", assign_line)
    base_indent = indent_match.group(1) if indent_match else ""
    inner_indent = base_indent + "    "
    # Build new assignment source
    new_list_src = format_prefix_list(merged, inner_indent)
    new_assign = f"{base_indent}trusted_host_prefixes = {new_list_src}"
    # Replace the old slice with the new assignment
    new_lines = lines[:start_line] + [new_assign] + lines[end_line:]
    return "\n".join(new_lines) + "\n"

def main():
    parser = argparse.ArgumentParser(
        description="Update core/hooks/pre_tool_hook.py to add relative trusted host prefixes."
    )
    parser.add_argument(
        "hook_path",
        nargs="?",
        default=os.path.join("core", "hooks", "pre_tool_hook.py"),
        help="Path to the pre_tool_hook.py file (default: core/hooks/pre_tool_hook.py)",
    )
    args = parser.parse_args()

    # Prefixes to be added (relative to repository root)
    prefixes_to_add = [
        "python3 core/",
        "python3 core/engine/diagnostic_runner.py",
        "python3 core/verify/",
        "python3 -m py_compile",
        "pytest",
    ]

    try:
        original_content = load_file(args.hook_path)
        updated_content = update_trusted_prefixes(original_content, prefixes_to_add)
        if original_content == updated_content:
            print("No changes required; all prefixes already present.")
            return 0
        write_file(args.hook_path, updated_content)
        print(f"Successfully updated '{args.hook_path}'.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
