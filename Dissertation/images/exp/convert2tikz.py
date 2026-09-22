#!/usr/bin/env python3
"""Convert graphviz dot files into LaTeX/TikZ node-graph code.

The resulting TikZ code follows a fixed structure (predefined preamble,
a list of \\node{} statements laid out using relative positioning, a list
of \\draw[edge] statements, and the \\end{tikzpicture}).

Usage:
    python ./convert2tikz.py ./dir-with-dots --out-dir ./dir-with-tikz
"""

import argparse
import os
import re
from collections import deque

PREAMBLE = r"""\begin{tikzpicture}[
    node distance=1.0cm and 1.0cm,
    box/.style={
      rectangle,
      draw,
      very thick,
      inner sep=3pt,
      font=\small,
      align=center
    },
    edge/.style={->, very thick, >={Latex[length=2.5mm]}}
  ]
"""

POSTAMBLE = r"""\end{tikzpicture}
"""

# Name plus optional label="..." (name may occur with or without a trailing ;).
_NODE_RE = re.compile(
    r"(?P<name>\w+)\s*\[\s*[^\]]*?label\s*=\s*\"(?P<label>[^\"]*)\"", re.IGNORECASE
)

# "A -> B" possibly with an attribute block, e.g. "A->B[style=bold]".
_EDGE_RE = re.compile(
    r"(?P<src>\w+)\s*->\s*(?P<dst>\w+)", re.IGNORECASE
)


def parse_label(dot_label):
    """Turn a dot label like ``R10_{[x, x+8)}^{0x...}`` into a ``$...$`` math string."""
    if "^" in dot_label:
        body, _, sup = dot_label.rpartition("^")
        sup = sup.strip()
        if sup.startswith("{") and sup.endswith("}"):
            sup = sup[1:-1]
    else:
        body, sup = dot_label, ""

    def texify(s):
        # keep the comma, but turn the following space(s) into a thin space.
        return re.sub(r",\s*", r",\\,", s)

    body = texify(body.strip())
    if sup:
        sup = texify(sup.strip())
        return "$" + body + "^{\\texttt{" + sup + "}}$"
    return "$" + body + "$"


def _offset_preferences():
    """Offsets tried around a parent's column when placing a row of parents.

    The offset 0 means "directly below" (the anchor), then extend one unit
    to the right, one to the left, two to the right, two to the left, and so
    on. Returning right/left alternately keeps growing branches balanced.
    """
    i = 1
    while True:
        yield 0
        yield i
        yield -i
        i += 1


def build_layout(dot_graph):
    """Assign a (level, column) to every node, then a relative placement.

    Edges ``A -> B`` mean ``A`` is a parent of ``B`` (drawn below it), so the
    graph rooted at the node with no outgoing edges. Each node's parents form
    a horizontal row directly beneath it:

      * the first-listed parent is placed ``below`` the node (the anchor),
      * each further parent is placed to the ``left``/``right`` of the anchor,
        choosing the side and distance that keeps column ``level`` cells free
        so different subtrees can never overlap.
    """
    nodes, edges = dot_graph
    parents = {n: [] for n in nodes}   # parents[child] = nodes drawn below child
    out_deg = {n: 0 for n in nodes}
    for src, dst in edges:
        parents[dst].append(src)
        out_deg[src] += 1

    roots = [n for n in nodes if out_deg[n] == 0]

    occupied = {}      # (level, column) -> node id
    info = {}          # node id -> dict(level, column, parent)
    queue = deque()
    for root in roots:
        if root in info:
            continue
        info[root] = {"level": 0, "column": 0, "parent": None}
        occupied[(0, 0)] = root
        queue.append(root)

    drawn = []         # ordered output list of node ids
    while queue:
        node = queue.popleft()
        if node not in info:
            continue
        drawn.append(node)
        lvl, col = info[node]["level"], info[node]["column"]
        offspring = parents[node]
        if not offspring:
            continue

        row_level = lvl + 1
        anchor = offspring[0]
        for i, child in enumerate(offspring):
            if child in info:
                continue
            # Pick the nearest free column for this child on the parent row,
            # skipping columns already occupied at that level.
            for off in _offset_preferences():
                cand = col + off
                if (row_level, cand) not in occupied:
                    chosen = cand
                    break
            info[child] = {"level": row_level, "column": chosen,
                           "parent": node}
            occupied[(row_level, chosen)] = child
            queue.append(child)
    return drawn, info, parents


def directive_for(child, info, parents):
    """Return the (relation, ref, distance) TikZ placement for ``child``."""
    par = info[child]["parent"]
    if par is None:                      # the root
        return None
    siblings = parents[par]
    anchor = siblings[0]
    delta = info[child]["column"] - info[par]["column"]
    if child is anchor:
        return ("below", par, 0)
    if delta > 0:
        return ("right", anchor, delta)
    return ("left", anchor, -delta)


def render_tikz(dot_graph):
    nodes, edges = dot_graph
    drawn, info, parents = build_layout(dot_graph)

    directives = {n: directive_for(n, info, parents) for n in drawn}

    lines = [PREAMBLE]
    for i, name in enumerate(drawn):
        math = parse_label(nodes[name])
        directive = directives[name]
        if directive is None:
            spec = ""
        else:
            relation, ref, dist = directive
            if relation == "below":
                spec = "below=of {}".format(ref)
            elif dist == 1:
                spec = "{}=of {}".format(relation, ref)
            else:
                spec = "{}={} of {}".format(relation, dist, ref)
        if spec:
            lines.append("  \\node[box, {}]  ({})".format(spec, name))
            lines.append("  {{{}}};".format(math))
        else:
            lines.append("  \\node[box] ({})".format(name))
            lines.append("  {{{}}};".format(math))
        if i != len(drawn) - 1:
            lines.append("")

    lines.append("")
    for src, dst in edges:
        lines.append("  \\draw[edge] ({}) -- ({});".format(src, dst))
    lines.append("")
    lines.append(POSTAMBLE)
    return "\n".join(lines)


def parse_dot(text):
    """Parse dot source into (node_name -> label, edge list)."""
    nodes = {}
    for m in _NODE_RE.finditer(text):
        nodes.setdefault(m.group("name"), m.group("label"))
    edges = []
    for m in _EDGE_RE.finditer(text):
        edges.append((m.group("src"), m.group("dst")))
    return nodes, edges


def main():
    parser = argparse.ArgumentParser(
        description="Convert graphviz dot graphs into TikZ node-graph code.")
    parser.add_argument("in_dir", help="directory containing the dot files")
    parser.add_argument("--out-dir", required=True,
                        help="directory where the tikz files are written")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    for filename in sorted(os.listdir(args.in_dir)):
        if not filename.endswith(".dot"):
            continue
        src = os.path.join(args.in_dir, filename)
        dst = os.path.join(args.out_dir, os.path.splitext(filename)[0] + ".tex")
        with open(src, "r", encoding="utf-8") as fh:
            dot_graph = parse_dot(fh.read())
        result = render_tikz(dot_graph)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(result)
        print("wrote {}".format(dst))


if __name__ == "__main__":
    main()