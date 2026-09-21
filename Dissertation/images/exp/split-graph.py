#!/usr/bin/env python3
"""
split-graph.py

Parses a DOT file describing a state graph, identifies all sink nodes (nodes with no
outgoing edges, typically named h*), and for each such sink creates a subgraph
containing all nodes that can reach it (reverse reachability). The sink node itself
is removed from the output. The generated subgraph files are named
`cluster-<idx1>-<idx2>-...dot` where the indices correspond to the
`ClusterizedReads` subgraphs that contributed at least one node to the subgraph.

Usage:
    python split-graph.py ./stategraph-full.dot --out-dir ./cluster
"""

"""AI request:
write python code, which parses graph description in dot format and splits this graph into N subgraphs with the following rules:
1. There are as many subgraphs as nodes with no outcoming edges. (they are `h*` nodes)
2. Subgraph consists of the nodes, node `h*` is reachable from
3. There is no `subgraph ClusterizedReads...` in subgraph file, all nodes are in the scope of `digraph`
3.5. Keep edges from selected nodes. But remove `h*` nodes from resulted file
4. The name of the file with subgraph is formed as follows: `cluster-<list of ClusterizedReads idx>.dot`
where list of ClusterizedReads idx is a list of removed `subgraph ClusterizedReadsIDX` structures within one subgraph file.
5. Usage: `python split-graph.py ./stategraph-full.dot --out-dir ./cluster`
All generated files are placed in `out-dir`

For example stategraph-full contains full graph
One of the resulted file is cluster-0.dot:
```
digraph unnamed {
rankdir=BT;
	Node1[style=bold,shape=box,group="Node",label="R04_{[y, y+4)}^{0xDEE7}"];
	Node2[style=bold,shape=box,group="Node",label="R07_{[y, y+1)}^{0x9}"];
	Node2 ->Node1 [style=bold]
}
```
and file cluster-18-19-20-21.dot with:
```
digraph unnamed {
rankdir=BT;
	Node44[style=bold,shape=box,group="Node",label="R10_{[x, x+8)}^{0x20e648dc9a7f23f9}"];
	Node45[style=bold,shape=box,group="Node",label="R02_{[x, x+8)}^{0x20e648dccb5f722e}"];
	Node46[style=bold,shape=box,group="Node",label="R22_{[x+2, x+4)}^{0xffffffffffffcb5f}"];
	Node47[style=bold,shape=box,group="Node",label="R02_{[x, x+8)}^{0x209548dccb5f722e}"];
	Node48[style=bold,shape=box,group="Node",label="R22_{[x+2, x+4)}^{0xffffffffffffcb5f}"];
	Node49[style=bold,shape=box,group="Node",label="R22_{[x+2, x+4)}^{0xffffffffffff9a7f}"];
	Node50[style=bold,shape=box,group="Node",label="R02_{[x, x+8)}^{0x209548dccb5f722e}"];
	Node51[style=bold,shape=box,group="Node",label="R02_{[x, x+8)}^{0x20e648dccb5f722e}"];
	Node45->Node44[style=bold]
	Node47->Node44[style=bold]
	Node49->Node44[style=bold]
	Node46->Node45[style=bold]
	Node48->Node47[style=bold]
	Node50->Node49[style=bold]
	Node51->Node49[style=bold]
}
```
and other files
"""

import re
import argparse
import os
from collections import defaultdict

def parse_dot_file(filepath):
    """
    Parse the DOT file and extract:
      - nodes: dict node_id -> {'def': str, 'cluster': int or None, 'order': int}
      - edges: list of {'src': str, 'tgt': str, 'def': str, 'order': int}
    """
    nodes = {}
    edges = []
    current_cluster = None
    depth = 0
    node_order = 0
    edge_order = 0

    # Regex patterns
    node_pattern = re.compile(r'^\s*(\w+)\s*\[.*\]\s*;?\s*$')
    edge_pattern = re.compile(r'(\w+)\s*->\s*(\w+)')
    cluster_pattern = re.compile(r'subgraph\s+ClusterizedReads(\d+)')

    with open(filepath, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            # Check for subgraph start (ClusterizedReadsX)
            m = cluster_pattern.search(stripped)
            if m:
                current_cluster = int(m.group(1))

            # Check for edge
            if '->' in stripped:
                m = edge_pattern.search(stripped)
                if m:
                    src, tgt = m.group(1), m.group(2)
                    edges.append({
                        'src': src,
                        'tgt': tgt,
                        'def': stripped,
                        'order': edge_order
                    })
                    edge_order += 1
            else:
                # Check for node definition
                m = node_pattern.match(stripped)
                if m:
                    node_id = m.group(1)
                    nodes[node_id] = {
                        'def': stripped,
                        'cluster': current_cluster,
                        'order': node_order
                    }
                    node_order += 1

            # Update brace depth
            depth += stripped.count('{')
            depth -= stripped.count('}')
            # When we close a ClusterizedReads subgraph, reset current_cluster
            if depth == 1 and current_cluster is not None:
                current_cluster = None

    return nodes, edges


def main():
    parser = argparse.ArgumentParser(
        description='Split DOT graph into subgraphs based on sink (h*) nodes.'
    )
    parser.add_argument('input_file', help='Path to the input DOT file')
    parser.add_argument('--out-dir', required=True,
                        help='Output directory for subgraph files')
    args = parser.parse_args()

    nodes, edges = parse_dot_file(args.input_file)

    # Build reverse adjacency list (predecessors)
    predecessors = defaultdict(list)
    for e in edges:
        predecessors[e['tgt']].append(e['src'])

    # Compute out-degree
    out_degree = defaultdict(int)
    for e in edges:
        out_degree[e['src']] += 1

    # Sink nodes are those with out-degree 0
    h_nodes = [nid for nid in nodes if out_degree.get(nid, 0) == 0]

    os.makedirs(args.out_dir, exist_ok=True)

    for h in h_nodes:
        # Reverse DFS to find all nodes that can reach h
        ancestors = set()
        stack = [h]
        while stack:
            node = stack.pop()
            if node not in ancestors:
                ancestors.add(node)
                for pred in predecessors[node]:
                    if pred not in ancestors:
                        stack.append(pred)

        # Remove the sink node itself
        ancestors.discard(h)
        sub_nodes = ancestors
        if not sub_nodes:
            continue

        # Edges whose both endpoints are in sub_nodes
        sub_edges = [
            e for e in edges
            if e['src'] in sub_nodes and e['tgt'] in sub_nodes
        ]

        # Collect the ClusterizedReads indices present in this subgraph
        clusters = set()
        for nid in sub_nodes:
            cl = nodes[nid]['cluster']
            if cl is not None:
                clusters.add(cl)

        # Build output filename
        if clusters:
            cluster_str = '-'.join(str(c) for c in sorted(clusters))
        else:
            cluster_str = ''
        filename = f"cluster-{cluster_str}.dot"
        filepath = os.path.join(args.out_dir, filename)

        # Output nodes and edges in their original order
        sorted_nodes = sorted(sub_nodes, key=lambda nid: nodes[nid]['order'])
        sorted_edges = sorted(sub_edges, key=lambda e: e['order'])

        with open(filepath, 'w') as f:
            f.write("digraph unnamed {\n")
            f.write("rankdir=BT;\n")
            for nid in sorted_nodes:
                f.write("\t" + nodes[nid]['def'] + "\n")
            for e in sorted_edges:
                f.write("\t" + e['def'] + "\n")
            f.write("}\n")

        print(f"Generated {filepath}")


if __name__ == '__main__':
    main()
