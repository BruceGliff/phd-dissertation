#!/usr/bin/env python3
"""
generate-table.py

Parses a DOT file and generates a YAML table with entries of the form:

R<XX>_i^j:
  id: NodeId
  value: Value
  op: R<XX>

where j is a unique identifier for the data (the value),
and i is a sequential counter for nodes sharing the same value.

Usage:
    generate-table.py dotfile.dot -o table.yaml
"""

import argparse
import re
import sys


def parse_dot_file(filepath):
    """Parse the DOT file and extract node information."""
    with open(filepath, 'r') as f:
        content = f.read()

    node_pattern = re.compile(
        r'Node(\d+)\s*\[\s*style\s*=\s*bold\s*,\s*shape\s*=\s*box\s*,\s*'
        r'group\s*=\s*"Node"\s*,\s*label\s*=\s*"([^"]+)"\s*\]\s*;'
    )

    # Label format: R04_{[y, y+4)}^{0xDEE7}
    # The range can contain ')' and other characters, so we match
    # everything between '_{' and '}^'.
    label_pattern = re.compile(
        r'^(R\d+)_\{(.+?)\}\^\{([^}]+)\}$'
    )

    nodes = []
    for match in node_pattern.finditer(content):
        node_id = int(match.group(1))
        label = match.group(2)
        label_match = label_pattern.match(label)
        if label_match:
            op = label_match.group(1)
            rng = label_match.group(2)
            value = label_match.group(3)
            nodes.append({
                'id': f'Node{node_id}',
                'op': op,
                'range': rng,
                'value': value,
            })
        else:
            print(f"Warning: Could not parse label: {label}", file=sys.stderr)

    return nodes


def generate_yaml(nodes):
    """Generate YAML output from parsed nodes."""
    # op -> {value: j_index}
    op_value_to_j = {}
    j_counters = {}

    # (op, j) -> i counter
    i_counters = {}

    # First pass: assign j and i indices
    for node in nodes:
        op = node['op']
        value = node['value']

        if op not in op_value_to_j:
            op_value_to_j[op] = {}
            j_counters[op] = 0

        if value not in op_value_to_j[op]:
            op_value_to_j[op][value] = j_counters[op]
            j_counters[op] += 1

        j = op_value_to_j[op][value]

        i_key = (op, j)
        if i_key not in i_counters:
            i_counters[i_key] = 0

        i = i_counters[i_key]
        i_counters[i_key] += 1

        node['i'] = i
        node['j'] = j

    # Second pass: generate YAML lines
    lines = []
    for node in nodes:
        key = f"{node['op']}_{{{node['i']}}}^{{{node['j']}}}"
        lines.append(f"{key}:")
        lines.append(f"  id: {node['id']}")
        lines.append(f"  value: {node['value']}")
        lines.append(f"  op: {node['op']}")

    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(
        description='Generate a YAML table from a DOT stategraph file.'
    )
    parser.add_argument(
        'dotfile',
        help='Path to the input DOT file (e.g., stategraph-final.dot)'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Path to the output YAML file (e.g., table.yaml)'
    )
    args = parser.parse_args()

    nodes = parse_dot_file(args.dotfile)
    yaml_output = generate_yaml(nodes)

    with open(args.output, 'w') as f:
        f.write(yaml_output)

    print(f"Wrote {len(nodes)} entries to {args.output}")


if __name__ == '__main__':
    main()
