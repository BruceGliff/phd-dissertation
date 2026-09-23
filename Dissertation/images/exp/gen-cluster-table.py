#!/usr/bin/env python3
"""
gen-cluster-table.py

Parses tikz files (nodes + edges) and generates a YAML table listing,
for each head node (a node with no incoming edges), all nodes reachable
from it.

Format of nodes:
    \\node[...]  (Node1)
    {$R04_{0}^{0}$};

Format of edges:
    \\draw[edge] (Node2) -- (Node1);   # Node1 is reachable from Node2

Head node indices are taken from each filename, e.g. `cluster-0.tex`
yields index 0, and `cluster-26-27-28-29.tex` yields 26, 27, 28, 29.
Heads appear in the file in the same order; the k-th head maps to the
k-th index of the filename.

Usage:
    gen-cluster-table.py directory-with-tikz-files -o cluster-table.yaml
"""

import argparse
import glob
import os
import re
import subprocess
import sys


def find_matching_brace(text, start):
    """Return the index of the '}' matching '{' at position start."""
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
    """Return the index of the ']' matching '[' at position start,
    skipping over brace groups so ']' inside braces are ignored."""
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


def extract_filename_indices(filename):
    """Return the list of head-node indices encoded in a filename like
    'cluster-26-27-28-29.tex' -> [26, 27, 28, 29]."""
    base = os.path.basename(filename)
    base = base.rsplit('.', 1)[0]
    nums = re.findall(r'\d+', base)
    return [int(n) for n in nums]


def parse_content(content):
    """Parse nodes and edges from tikz content.

    Returns:
        nodes: {node_id (int): label}
        edges: list of (src_id, dst_id) meaning dst is reachable from src
    """
    nodes = {}

    def iter_node_bodies():
        i = 0
        while True:
            idx = content.find('\\node[', i)
            if idx == -1:
                return
            bracket_end = find_matching_bracket(
                content, idx + len('\\node[') - 1)
            if bracket_end == -1:
                return
            rest = content[bracket_end + 1:]
            id_match = re.search(r'\(\s*Node(\d+)\s*\)', rest)
            if not id_match:
                i = idx + len('\\node[')
                continue
            label_start = bracket_end + 1 + id_match.end()
            brace = re.search(r'\{', content[label_start:])
            if not brace:
                i = idx + len('\\node[')
                continue
            open_brace = label_start + brace.start()
            close_brace = find_matching_brace(content, open_brace)
            if close_brace == -1:
                return
            yield id_match.group(1), content[open_brace + 1:close_brace]
            i = close_brace + 1

    for node_id_str, body in iter_node_bodies():
        nodes[int(node_id_str)] = body.strip()

    edges = []
    for m in re.finditer(
            r'\\draw\[[^\]]*\]\s*\(\s*Node(\d+)\s*\)\s*--\s*\(\s*Node(\d+)\s*\)\s*;',
            content):
        edges.append((int(m.group(1)), int(m.group(2))))

    return nodes, edges


def find_head_nodes(edges):
    """Return node ids that have no incoming edges (nothing points at
    them). Head nodes keep the same order as their first edge occurrence;
    nodes with no edges at all are treated as isolated heads in the order
    they were defined in the file (handled by caller)."""
    with_incoming = {dst for (_, dst) in edges}
    seen = set()
    heads = []
    for (src, _) in edges:
        if src not in with_incoming and src not in seen:
            seen.add(src)
            heads.append(src)
    return heads, with_incoming


def reachable_from(start, edges):
    """Return nodes reachable from `start` following edges, in DFS
    pre-order (start first, then reachable downstream)."""
    adj = {}
    for (src, dst) in edges:
        adj.setdefault(src, []).append(dst)
    for src in adj:
        adj[src].sort()

    result = []
    visited = set()

    def dfs(node):
        if node in visited:
            return
        visited.add(node)
        result.append(node)
        for nxt in adj.get(node, []):
            dfs(nxt)

    dfs(start)
    return result


def render(label):
    """Render a node label. `label` already includes the surrounding
    math-mode dollars (e.g. '$R04_{0}^{0}$'), returned unchanged."""
    return label


def process_file(filepath):
    """Parse one tikz file and return ordered list of
    (index, [labels in reachable order])."""
    with open(filepath, 'r') as f:
        content = f.read()

    nodes, edges = parse_content(content)
    head_edges, with_incoming = find_head_nodes(edges)

    # Heads that appear as sources but have no incoming edges.
    heads = list(head_edges)

    # Isolated nodes (no edges at all) - treat as their own head.
    defined_order = list(nodes.keys())
    isolated = [n for n in defined_order if n not in with_incoming
                and not any(s == n for s, _ in edges)]
    heads.extend(isolated)

    indices = extract_filename_indices(filepath)

    results = []
    for k, head in enumerate(heads):
        index = indices[k] if k < len(indices) else indices[-1]
        labels = [nodes[n] for n in reachable_from(head, edges)]
        labels.sort()
        results.append((index, labels))

    return results


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Generate a cluster reachability table (YAML) from tikz files.'
        )
    )
    parser.add_argument(
        'directory',
        help='Directory containing tikz files',
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Path to the output YAML file',
    )
    args = parser.parse_args()

    files = sorted(
        glob.glob(os.path.join(args.directory, '*.tex'))
        + glob.glob(os.path.join(args.directory, '*.tikz'))
    )

    lines = []
    for filepath in files:
        print(f"Processing: {os.path.basename(filepath)}", file=sys.stderr)
        for index, labels in process_file(filepath):
            lines.append(f'$C_{{3}}^{{{index}}}$:')
            for i, label in enumerate(labels):
                prefix = ' - ' if i == 0 else '   '
                lines.append(f'{prefix}{render(label)}')

    output = '\n'.join(lines) + '\n'
    with open(args.output, 'w') as f:
        f.write(output)

    print(f"Wrote output to {args.output}")


if __name__ == '__main__':
    main()