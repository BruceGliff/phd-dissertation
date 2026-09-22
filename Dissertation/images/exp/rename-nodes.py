#!/usr/bin/env python3
"""
rename-nodes.py

Traverses all tikz files in a given directory and renames each node's
label according to a value table described in YAML format.

The value table maps dict-keys to nodes, e.g.:

    R22_3^1:
      id: Node52
      value: 0xffffffffffff9a7f
      op: R22

For each node definition like

    \\node[...]  (Node52)
    {$R22_{[x+2,\\,x+4)}^{\\texttt{0xffffffffffff9a7f}}$};

the label is replaced with the dict-key from the table (in math mode):

    \\node[...]  (Node52)
    {$R22_3^1$};

Each processed file is written to the output directory under the same
name.

Usage:
    rename-nodes.py autogen-colored -o autogen-renamed --table value-table.yaml
"""

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML is required. Install it with `pip install pyyaml`.",
        file=sys.stderr,
    )
    sys.exit(1)


def build_id_to_key(table):
    """Return a mapping from node id -> dict-key from the YAML table."""
    id_to_key = {}
    for key, record in table.items():
        node_id = record.get('id')
        if node_id is None:
            print(f"Warning: record {key!r} has no 'id' field", file=sys.stderr)
            continue
        id_to_key[node_id] = key
    return id_to_key


def find_matching_brace(text, start):
    """Return index of the '}' matching '{' at position start."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def find_matching_bracket(text, start):
    """Return index of the ']' matching '[' at position start.

    Braces inside the options (e.g. path picture={{...}}) are skipped so
    that ']' characters inside them do not confuse the match.
    """
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == '{':
            close = find_matching_brace(text, i)
            if close == -1:
                return -1
            i = close + 1
            continue
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def process_content(content, id_to_key):
    """Replace node labels in tikz content using the id->key mapping.

    Returns the modified content and the number of replaced nodes.
    """
    node_pattern = re.compile(r'\\node\[')
    out = []
    last = 0
    replaced = 0

    for match in node_pattern.finditer(content):
        start = match.start()
        out.append(content[last:start])

        bracket_end = find_matching_bracket(content, start + len('\\node[') - 1)
        if bracket_end == -1:
            out.append(content[start:])
            last = start
            break

        id_match = re.search(r'\((Node\d+)\)', content[bracket_end + 1:])
        if not id_match:
            out.append(content[start:bracket_end + 1])
            last = bracket_end + 1
            continue

        node_id = id_match.group(1)
        label_start = bracket_end + 1 + id_match.end()

        brace_search = re.search(r'\{', content[label_start:])
        if not brace_search:
            out.append(content[start:bracket_end + 1])
            last = bracket_end + 1
            continue

        open_brace = label_start + brace_search.start()
        close_brace = find_matching_brace(content, open_brace)
        if close_brace == -1:
            out.append(content[start:])
            last = start
            break

        semicolon = close_brace + 1
        if semicolon < len(content) and content[semicolon] == ';':
            semicolon += 1

        out.append(content[start:open_brace])

        new_key = id_to_key.get(node_id)
        if new_key:
            out.append(f'{{${new_key}$}}')
            if semicolon > close_brace + 1:
                out.append(';')
            replaced += 1
        else:
            out.append(content[open_brace:semicolon])

        last = semicolon

    out.append(content[last:])
    return ''.join(out), replaced


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Rename node labels in tikz files according to a value table.'
        )
    )
    parser.add_argument(
        'indir',
        help='Input directory containing tikz files'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output directory (created if missing)'
    )
    parser.add_argument(
        '--table',
        required=True,
        help='Path to the YAML value table'
    )
    args = parser.parse_args()

    with open(args.table, 'r') as f:
        table = yaml.safe_load(f)

    id_to_key = build_id_to_key(table)

    os.makedirs(args.output, exist_ok=True)

    for name in sorted(os.listdir(args.indir)):
        src = os.path.join(args.indir, name)
        if not os.path.isfile(src):
            continue
        if not (name.endswith('.tex') or name.endswith('.tikz')):
            continue

        with open(src, 'r') as f:
            content = f.read()

        new_content, replaced = process_content(content, id_to_key)

        dst = os.path.join(args.output, name)
        with open(dst, 'w') as f:
            f.write(new_content)

        print(f"{name}: replaced {replaced} node label(s)")


if __name__ == '__main__':
    main()