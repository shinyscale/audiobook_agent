#!/usr/bin/env python3
"""
Identity Graph Visualization — D3.js Force-Directed Graph

Generates an interactive HTML file from identity_graph.json.

Usage:
    python graph_viz.py output/american_sir/identity_graph.json
    python graph_viz.py output/american_sir/identity_graph.json -o custom_output.html
"""

import json
import sys
from pathlib import Path

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Identity Graph — {title}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; overflow: hidden; }
svg { width: 100vw; height: 100vh; display: block; }

/* Tooltip */
#tooltip {
    position: absolute; display: none; pointer-events: none;
    background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
    padding: 10px 14px; font-size: 13px; max-width: 360px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 100;
}
#tooltip .tt-title { font-weight: 700; font-size: 15px; color: #e94560; margin-bottom: 6px; }
#tooltip .tt-row { margin: 3px 0; }
#tooltip .tt-label { color: #8899aa; }

/* Detail panel */
#detail {
    position: absolute; top: 12px; right: 12px; width: 300px;
    background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
    padding: 16px; display: none; z-index: 90;
    box-shadow: 0 4px 16px rgba(0,0,0,0.6); max-height: 80vh; overflow-y: auto;
}
#detail .close { float: right; cursor: pointer; color: #e94560; font-size: 18px; }
#detail h3 { color: #e94560; margin-bottom: 8px; font-size: 16px; }
#detail .section { margin: 8px 0; }
#detail .section-title { color: #53a8b6; font-size: 12px; text-transform: uppercase; margin-bottom: 4px; }
#detail .alias { display: inline-block; background: #0f3460; border-radius: 3px; padding: 2px 6px; margin: 2px; font-size: 12px; }
#detail .edge-item { margin: 4px 0; font-size: 12px; padding: 4px 6px; border-radius: 3px; }
#detail .edge-merge { background: rgba(76,175,80,0.15); border-left: 3px solid #4caf50; }
#detail .edge-constraint { background: rgba(244,67,54,0.15); border-left: 3px solid #f44336; }

/* Legend */
#legend {
    position: absolute; bottom: 12px; left: 12px;
    background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
    padding: 12px 16px; font-size: 12px; z-index: 90;
}
#legend h4 { color: #53a8b6; margin-bottom: 6px; }
#legend .item { display: flex; align-items: center; margin: 4px 0; }
#legend .swatch { width: 14px; height: 14px; border-radius: 3px; margin-right: 8px; flex-shrink: 0; }
#legend .line-swatch { width: 28px; height: 3px; margin-right: 8px; flex-shrink: 0; }

/* Stats bar */
#stats {
    position: absolute; top: 12px; left: 12px;
    background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
    padding: 10px 16px; font-size: 13px; z-index: 90;
}
#stats span { margin-right: 16px; }
#stats .num { color: #e94560; font-weight: 700; }
</style>
</head>
<body>

<div id="stats"></div>
<div id="tooltip"></div>
<div id="detail"></div>
<div id="legend">
    <h4>Legend</h4>
    <div class="item"><div class="swatch" style="background:#4fc3f7;"></div>Main Cast</div>
    <div class="item"><div class="swatch" style="background:#78909c;"></div>Supporting</div>
    <div class="item"><div class="swatch" style="background:#ffd54f; border:2px solid #ff8f00;"></div>Narrator</div>
    <div class="item"><div class="line-swatch" style="background:#4caf50;"></div>Merge Edge</div>
    <div class="item"><div class="line-swatch" style="background:#f44336; border-top:2px dashed #f44336; height:0;"></div>Constraint Edge</div>
</div>
<svg id="graph"></svg>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const DATA = __GRAPH_DATA__;

const svg = d3.select("#graph");
const width = window.innerWidth;
const height = window.innerHeight;
svg.attr("viewBox", [0, 0, width, height]);

const g = svg.append("g");

// Zoom
svg.call(d3.zoom()
    .scaleExtent([0.2, 5])
    .on("zoom", (e) => g.attr("transform", e.transform)));

// Nodes
const nodes = DATA.graph.nodes.map(d => ({...d}));
const nodeById = new Map(nodes.map(n => [n.id, n]));

// Merge edges
const mergeEdges = DATA.graph.merge_edges
    .filter(e => nodeById.has(e.source) && nodeById.has(e.target))
    .map(e => ({...e, source: e.source, target: e.target}));

// Constraint edges
const constraintEdges = DATA.graph.constraint_edges
    .filter(e => nodeById.has(e.source) && nodeById.has(e.target))
    .map(e => ({...e, source: e.source, target: e.target}));

// Merge groups (for cluster highlighting)
const mergeGroups = (DATA.merge_groups || []).filter(g => g.members.length > 1);

// Stats
const stats = DATA.stats || {};
document.getElementById("stats").innerHTML =
    `<span>Nodes: <span class="num">${nodes.length}</span></span>` +
    `<span>Merge Edges: <span class="num">${mergeEdges.length}</span></span>` +
    `<span>Constraints: <span class="num">${constraintEdges.length}</span></span>` +
    `<span>Merge Groups: <span class="num">${mergeGroups.length}</span></span>`;

// Scale for node radius
const mentionExtent = d3.extent(nodes, d => d.mentions);
const rScale = d3.scaleSqrt()
    .domain([mentionExtent[0] || 1, mentionExtent[1] || 100])
    .range([6, 28]);

// Force simulation
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(mergeEdges).id(d => d.id).distance(80).strength(0.4))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(d => rScale(d.mentions) + 4));

// Merge group hulls
const hullG = g.append("g").attr("class", "hulls");

// Constraint edges (dashed red)
const constraintLine = g.append("g")
    .selectAll("line")
    .data(constraintEdges)
    .join("line")
    .attr("stroke", "#f44336")
    .attr("stroke-width", d => Math.max(1, (d.strength || 0.5) * 3))
    .attr("stroke-dasharray", "6 4")
    .attr("stroke-opacity", 0.6)
    .on("mouseover", (event, d) => showTooltip(event, constraintTooltip(d)))
    .on("mouseout", hideTooltip);

// Merge edges (solid green)
const mergeLink = g.append("g")
    .selectAll("line")
    .data(mergeEdges)
    .join("line")
    .attr("stroke", "#4caf50")
    .attr("stroke-width", d => Math.max(1, (d.weight || 0.5) * 4))
    .attr("stroke-opacity", 0.7)
    .on("mouseover", (event, d) => showTooltip(event, mergeTooltip(d)))
    .on("mouseout", hideTooltip);

// Nodes
const node = g.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(d3.drag()
        .on("start", dragStart)
        .on("drag", dragging)
        .on("end", dragEnd));

node.append("circle")
    .attr("r", d => rScale(d.mentions))
    .attr("fill", d => d.is_narrator ? "#ffd54f" : d.is_main_cast ? "#4fc3f7" : "#78909c")
    .attr("stroke", d => d.is_narrator ? "#ff8f00" : "#fff")
    .attr("stroke-width", d => d.is_narrator ? 3 : 1.5)
    .attr("opacity", 0.9);

// Labels
node.append("text")
    .text(d => d.name)
    .attr("dy", d => rScale(d.mentions) + 14)
    .attr("text-anchor", "middle")
    .attr("fill", "#ccc")
    .attr("font-size", "11px")
    .attr("pointer-events", "none");

// Node interactions
node.on("mouseover", (event, d) => showTooltip(event, nodeTooltip(d)))
    .on("mouseout", hideTooltip)
    .on("click", (event, d) => showDetail(d));

// Tick
simulation.on("tick", () => {
    mergeLink
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    constraintLine
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    node.attr("transform", d => `translate(${d.x},${d.y})`);

    // Update hulls
    drawHulls();
});

function drawHulls() {
    hullG.selectAll("path").remove();
    mergeGroups.forEach(group => {
        const points = group.members
            .map(id => nodes.find(n => n.id === id))
            .filter(n => n && n.x !== undefined)
            .map(n => [n.x, n.y]);
        if (points.length < 2) return;
        // Pad points for hull visibility
        const padded = [];
        const pad = 18;
        points.forEach(([x, y]) => {
            padded.push([x - pad, y - pad], [x + pad, y - pad],
                        [x - pad, y + pad], [x + pad, y + pad]);
        });
        const hull = d3.polygonHull(padded);
        if (hull) {
            hullG.append("path")
                .attr("d", `M${hull.join("L")}Z`)
                .attr("fill", "rgba(76,175,80,0.08)")
                .attr("stroke", "rgba(76,175,80,0.25)")
                .attr("stroke-width", 1.5);
        }
    });
}

// Drag
function dragStart(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
function dragging(event, d) { d.fx = event.x; d.fy = event.y; }
function dragEnd(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }

// Tooltip
const tooltip = document.getElementById("tooltip");
function showTooltip(event, html) {
    tooltip.innerHTML = html;
    tooltip.style.display = "block";
    tooltip.style.left = (event.pageX + 12) + "px";
    tooltip.style.top = (event.pageY - 10) + "px";
}
function hideTooltip() { tooltip.style.display = "none"; }

function nodeTooltip(d) {
    const aliases = d.aliases.length ? d.aliases.join(", ") : "none";
    return `<div class="tt-title">${d.name}</div>` +
        `<div class="tt-row"><span class="tt-label">Mentions:</span> ${d.mentions}</div>` +
        `<div class="tt-row"><span class="tt-label">Cast:</span> ${d.is_main_cast ? "Main" : "Supporting"}</div>` +
        `<div class="tt-row"><span class="tt-label">Narrator:</span> ${d.is_narrator ? "Yes" : "No"}</div>` +
        `<div class="tt-row"><span class="tt-label">Aliases:</span> ${aliases}</div>`;
}
function mergeTooltip(d) {
    const src = nodeById.get(typeof d.source === "object" ? d.source.id : d.source);
    const tgt = nodeById.get(typeof d.target === "object" ? d.target.id : d.target);
    return `<div class="tt-title">Merge Edge</div>` +
        `<div class="tt-row">${src?.name || "?"} ↔ ${tgt?.name || "?"}</div>` +
        `<div class="tt-row"><span class="tt-label">Type:</span> ${d.type}</div>` +
        `<div class="tt-row"><span class="tt-label">Weight:</span> ${(d.weight || 0).toFixed(2)}</div>` +
        `<div class="tt-row"><span class="tt-label">Reason:</span> ${d.reason || ""}</div>`;
}
function constraintTooltip(d) {
    const src = nodeById.get(typeof d.source === "object" ? d.source.id : d.source);
    const tgt = nodeById.get(typeof d.target === "object" ? d.target.id : d.target);
    return `<div class="tt-title" style="color:#f44336">Constraint Edge</div>` +
        `<div class="tt-row">${src?.name || "?"} ≠ ${tgt?.name || "?"}</div>` +
        `<div class="tt-row"><span class="tt-label">Type:</span> ${d.type}</div>` +
        `<div class="tt-row"><span class="tt-label">Strength:</span> ${(d.strength || 0).toFixed(2)}</div>` +
        `<div class="tt-row"><span class="tt-label">Reason:</span> ${d.reason || ""}</div>`;
}

// Detail panel
function showDetail(d) {
    const panel = document.getElementById("detail");
    const edges = mergeEdges.filter(e =>
        (typeof e.source === "object" ? e.source.id : e.source) === d.id ||
        (typeof e.target === "object" ? e.target.id : e.target) === d.id);
    const constraints = constraintEdges.filter(e =>
        (typeof e.source === "object" ? e.source.id : e.source) === d.id ||
        (typeof e.target === "object" ? e.target.id : e.target) === d.id);

    let html = `<span class="close" onclick="document.getElementById('detail').style.display='none'">&times;</span>`;
    html += `<h3>${d.name}</h3>`;
    html += `<div class="section"><div class="section-title">Info</div>`;
    html += `Mentions: ${d.mentions} | Cast: ${d.is_main_cast ? "Main" : "Supporting"}`;
    if (d.is_narrator) html += ` | <b>Narrator</b>`;
    html += `</div>`;

    if (d.aliases.length) {
        html += `<div class="section"><div class="section-title">Aliases</div>`;
        d.aliases.forEach(a => html += `<span class="alias">${a}</span>`);
        html += `</div>`;
    }

    // Merge group membership
    const group = mergeGroups.find(g => g.members.includes(d.id));
    if (group && group.members.length > 1) {
        html += `<div class="section"><div class="section-title">Merge Group</div>`;
        html += `Canonical: ${group.canonical_name}<br>`;
        html += `Members: ${group.members.length} | Evidence: ${group.evidence_count}`;
        if (group.constraints_overridden > 0) html += ` | Overridden: ${group.constraints_overridden}`;
        html += `</div>`;
    }

    if (edges.length) {
        html += `<div class="section"><div class="section-title">Merge Edges (${edges.length})</div>`;
        edges.forEach(e => {
            const other = (typeof e.source === "object" ? e.source.id : e.source) === d.id
                ? nodeById.get(typeof e.target === "object" ? e.target.id : e.target)
                : nodeById.get(typeof e.source === "object" ? e.source.id : e.source);
            html += `<div class="edge-item edge-merge">↔ ${other?.name || "?"} (${e.type}, w=${(e.weight||0).toFixed(2)})<br><small>${e.reason || ""}</small></div>`;
        });
        html += `</div>`;
    }

    if (constraints.length) {
        html += `<div class="section"><div class="section-title">Constraints (${constraints.length})</div>`;
        constraints.forEach(e => {
            const other = (typeof e.source === "object" ? e.source.id : e.source) === d.id
                ? nodeById.get(typeof e.target === "object" ? e.target.id : e.target)
                : nodeById.get(typeof e.source === "object" ? e.source.id : e.source);
            html += `<div class="edge-item edge-constraint">≠ ${other?.name || "?"} (${e.type}, s=${(e.strength||0).toFixed(2)})<br><small>${e.reason || ""}</small></div>`;
        });
        html += `</div>`;
    }

    panel.innerHTML = html;
    panel.style.display = "block";
}
</script>
</body>
</html>"""


def generate_html(graph_data: dict, title: str = "Identity Graph") -> str:
    """Generate HTML with embedded D3.js visualization."""
    json_str = json.dumps(graph_data, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("{title}", title)
    html = html.replace("__GRAPH_DATA__", json_str)
    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python graph_viz.py <identity_graph.json> [-o output.html]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    # Parse optional output path
    output_path = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])

    if output_path is None:
        output_path = input_path.with_suffix(".html")

    with open(input_path) as f:
        data = json.load(f)

    title = input_path.parent.name or "Identity Graph"
    html = generate_html(data, title)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {output_path}")
    print(f"  Nodes: {len(data.get('graph', {}).get('nodes', []))}")
    print(f"  Merge edges: {len(data.get('graph', {}).get('merge_edges', []))}")
    print(f"  Constraint edges: {len(data.get('graph', {}).get('constraint_edges', []))}")
    print(f"  Merge groups: {len(data.get('merge_groups', []))}")


if __name__ == "__main__":
    main()
