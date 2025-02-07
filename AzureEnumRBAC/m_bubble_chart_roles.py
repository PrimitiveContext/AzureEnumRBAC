#!/usr/bin/env python3
"""
m_bubble_chart_roles_all.py

Displays *all* roles in a bubble chart, regardless of assignment counts.

It calculates the count for each role by summing the number of scope entries.

Usage:
  python m_bubble_chart_roles_all.py [optional_input_file]

Default input: "output/i_combined_user_identities.json"
Output: "output/m_bubble_chart_roles.html"
"""

import os
import sys
import json
import math

def parse_bracketed_label(s: str) -> str:
    """Given '[4845]Virtual Machine Contributor', returns 'Virtual Machine Contributor'."""
    if not s.startswith("[") or "]" not in s:
        return s
    return s[s.index("]") + 1 :].strip()

def accumulate_role_assignments(rbac_obj: dict, role_assign_map: dict, role_scopes_map: dict):
    """
    For each role bracket key (like '[4845]Virtual Machine Contributor'):
      - parse label => 'Virtual Machine Contributor'
      - count sub-keys => that many assignments for that role
      - store scope strings
    """
    if not rbac_obj or not isinstance(rbac_obj, dict):
        return
    for role_bracket_key, sub_dict in rbac_obj.items():
        role_label = parse_bracketed_label(role_bracket_key)
        if not isinstance(sub_dict, dict):
            continue
        count_here = len(sub_dict)
        if count_here == 0:
            continue
        # Accumulate
        role_assign_map[role_label] = role_assign_map.get(role_label, 0) + count_here
        # Collect scope strings
        if role_label not in role_scopes_map:
            role_scopes_map[role_label] = set()
        for _scope_bracket, scope_str in sub_dict.items():
            role_scopes_map[role_label].add(scope_str)

def build_role_assignment_map(input_file: str):
    """
    Returns:
      role_assign_map => { "Virtual Machine Contributor": total_count, ... }
      role_scopes_map => { "Virtual Machine Contributor": set_of_scope_strings, ... }
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    role_assign_map = {}
    role_scopes_map = {}

    for _user_name, principal_map in data.items():
        for _pid, details in principal_map.items():
            rbac_obj = details.get("rbac", {})
            accumulate_role_assignments(rbac_obj, role_assign_map, role_scopes_map)

    return (role_assign_map, role_scopes_map)

def generate_roles_html(role_assign_map, role_scopes_map, out_html="output/m_bubble_chart_roles.html"):
    """
    Builds a bubble chart for all roles and writes to HTML.
    """
    # Build a list of role records
    role_list = []
    for rname, rcount in role_assign_map.items():
        scopes_set = role_scopes_map.get(rname, set())
        role_list.append({
            "roleName": rname,
            "assignmentCount": rcount,
            "scopes": sorted(list(scopes_set))
        })

    if not role_list:
        print("[INFO] No roles found at all.")
        return

    # Convert to JSON
    import json
    final_json = json.dumps(role_list, ensure_ascii=False)

    # Build the bubble chart
    html_template = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>All Roles Bubble Chart</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body {
      font-family: sans-serif;
      margin: 20px;
    }
    #chart {
      width: 1500px;
      height: 1000px;
      border: 1px solid #ccc;
      margin-bottom: 20px;
    }
    .tooltip {
      position: absolute;
      background: rgba(0,0,0,0.7);
      color: #fff;
      padding: 5px 8px;
      border-radius: 4px;
      pointer-events: none;
      font-size: 12px;
      z-index: 999;
      opacity: 0;
    }
  </style>
</head>
<body>
<h2>All Roles Bubble Chart</h2>
<p>Every discovered role is shown here, sized by its assignment count.</p>

<div id="chart"></div>
<div class="tooltip" id="tooltip"></div>

<script>
const roleData = {final_json};

const width = 3000, height = 2000;
const svg = d3.select("#chart")
  .append("svg")
  .attr("width", 1500)
  .attr("height", 1000)
  .attr("viewBox",[0,0,width,height]);

const tooltip = d3.select(".tooltip");

// find max assignmentCount
const maxCount = d3.max(roleData, d => d.assignmentCount) || 1;
const radiusScale = d3.scaleSqrt()
  .domain([0, maxCount])
  .range([0, 160]);

// color scale
const colorScale = d3.scaleOrdinal()
  .domain(roleData.map(d => d.roleName))
  .range(d3.quantize(d3.interpolateRainbow, roleData.length + 1));

let nodes = roleData.map((r,i) => {
  return {
    index: i,
    roleName: r.roleName,
    assignmentCount: r.assignmentCount,
    scopes: r.scopes,
    x: Math.random()*width,
    y: Math.random()*height,
    r: radiusScale(r.assignmentCount)
  };
});

const nodeG = svg.selectAll(".roleNode")
  .data(nodes)
  .enter()
  .append("g")
  .attr("class","roleNode");

nodeG.append("circle")
  .attr("r", d => d.r)
  .attr("fill", d => colorScale(d.roleName))
  .attr("stroke", "#333")
  .attr("stroke-width", 0.5)
  .on("mouseover", function(evt, d) {
    tooltip.style("opacity", 1);
    const scopesList = d.scopes.map(s => "- " + s).join("<br/>");
    const html = `
      <div><strong>Role:</strong> ${d.roleName}</div>
      <div><strong>AssignmentCount:</strong> ${d.assignmentCount}</div>
      <div><strong>Distinct Scopes:</strong><br/>${scopesList}</div>
    `;
    tooltip.html(html);
  })
  .on("mousemove", function(evt) {
    tooltip
      .style("left", (evt.pageX+10) + "px")
      .style("top", (evt.pageY+10) + "px");
  })
  .on("mouseout", function() {
    tooltip.style("opacity", 0);
  });

nodeG.each(function(d) {
  const g = d3.select(this);
  const textEl = g.append("text")
    .attr("text-anchor","middle")
    .attr("dy","0.4em")
    .text(d.roleName);

  let fontSize = 40;
  textEl.style("font-size", fontSize + "px");
  while(true) {
    const bbox = textEl.node().getBBox();
    const maxDim = Math.max(bbox.width,bbox.height);
    if(maxDim <= 2*d.r || fontSize<=1) break;
    fontSize--;
    textEl.style("font-size", fontSize+"px");
  }
});

const simulation = d3.forceSimulation(nodes)
  .force("center", d3.forceCenter(width/2,height/2))
  .force("x", d3.forceX(width/2).strength(0.2))
  .force("y", d3.forceY(height/2).strength(0.2))
  .force("charge", d3.forceManyBody().strength(0))
  .force("collision", d3.forceCollide().radius(d => d.r).strength(1))
  .on("tick", () => {
    nodes.forEach(d => {
      if(d.x<d.r) d.x=d.r;
      if(d.x>width-d.r) d.x=width-d.r;
      if(d.y<d.r) d.y=d.r;
      if(d.y>height-d.r) d.y=height-d.r;
    });
    nodeG.attr("transform", d => `translate(${d.x},${d.y})`);
  });
</script>
</body>
</html>
"""

    final_html = html_template.replace("{final_json}", final_json)

    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"[INFO] Wrote => {out_html}")
    print(f"[INFO] Total roles displayed: {len(role_list)}")

def main():
    """
    Usage:
      python m_bubble_chart_roles_all.py [optionalInputFile]

    Displays a bubble chart of all roles, sized by their assignment count.
    """
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "output/i_combined_user_identities.json"

    if not os.path.exists(input_file):
        print(f"[ERROR] File not found: {input_file}")
        sys.exit(1)

    role_assign_map, role_scopes_map = build_role_assignment_map(input_file)
    if not role_assign_map:
        print("[INFO] No roles discovered.")
        return

    generate_roles_html(role_assign_map, role_scopes_map, out_html="output/m_bubble_chart_roles.html")
    print("[INFO] Done! Open 'output/m_bubble_chart_roles.html' in your browser.")

if __name__ == "__main__":
    main()
