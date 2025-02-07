#!/usr/bin/env python3
"""
l_bubble_chart_users.py

Generates an above-average user bubble chart with pie slices per role.

- Merges multiple principal IDs per user from i_combined_user_identities.json.
- Sums up each user's total resource counts across roles.
- Computes the average totalResourceCount; filters out users below that average.
- Produces output/l_bubble_chart_users.html (pie-sliced bubble chart):
  - Each user = circle sized by total resource count.
  - Pie slices = each role portion of that total.
  - Hover over circle => tooltip with user's full role list.
  - Side role list => hover to highlight that role's slices in all circles.

Usage:
  python l_bubble_chart_users.py [optional_input_file]
    Default input: output/i_combined_user_identities.json
Output:
  output/l_bubble_chart_users.html
"""

import os
import sys
import json

def parse_bracketed_count(s: str) -> int:
    if not s.startswith("[") or "]" not in s:
        return 0
    try:
        inside = s[1 : s.index("]")]
        return int(inside)
    except ValueError:
        return 0

def parse_bracketed_label(s: str) -> str:
    if not s.startswith("[") or "]" not in s:
        return s
    return s[s.index("]")+1:]

def merge_principal_rbac(rbac_dict, role_map):
    """
    Merges the roles from one principal's RBAC into role_map.
    E.g. "[6]Contributor" => role_map["Contributor"] += 6
    """
    if not rbac_dict or not isinstance(rbac_dict, dict):
        return
    for role_key, _subdict in rbac_dict.items():
        cnt = parse_bracketed_count(role_key)
        lbl = parse_bracketed_label(role_key).strip()
        role_map[lbl] = role_map.get(lbl, 0) + cnt

def load_users_and_merge_principals(input_file: str):
    """
    Reads i_combined_user_identities.json from e.g. "output/i_combined_user_identities.json".
    Merges multiple principal IDs per user, summing roles into a single user record.
    Returns a list of user dicts:
      [
        {
          "userName": "Ayush Jha",
          "jobTitle": "...",
          "totalResourceCount": 7,
          "roles": [
             { "roleName": "Contributor", "count": 6 },
             { "roleName": "Storage File Data SMB Share Reader", "count": 1 }
          ]
        },
        ...
      ]
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_list = []
    for user_name, principal_map in data.items():
        role_map = {}
        job_title = ""
        for pid, details in principal_map.items():
            if not job_title:
                jt = details.get("jobTitle", "").strip()
                if jt:
                    job_title = jt
            rbac_obj = details.get("rbac", {})
            merge_principal_rbac(rbac_obj, role_map)

        total_count = sum(role_map.values())
        roles_list = [{"roleName":k, "count":v} for k,v in role_map.items()]
        user_list.append({
            "userName": user_name.strip().replace("_",""),
            "jobTitle": job_title,
            "totalResourceCount": total_count,
            "roles": roles_list
        })
    return user_list

def generate_above_avg_html(user_data, out_html="output/l_bubble_chart_users.html"):
    """
    Filters out users below average totalResourceCount.
    Writes a bubble chart with pie slices per role to out_html.
    """
    if not user_data:
        print("[INFO] No users found.")
        return

    counts = [u["totalResourceCount"] for u in user_data]
    avg = sum(counts)/len(counts) if counts else 0
    filtered = [u for u in user_data if u["totalResourceCount"] > avg]
    if not filtered:
        print(f"[INFO] No users above average ~{avg:.1f}.")
        return

    filtered_json = json.dumps(filtered, ensure_ascii=False)

    # Use .replace() to avoid Python interpreting JS braces as placeholders
    html_template = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Above Avg Users (~AVGCOUNT~)</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body {
      font-family: sans-serif;
      margin: 20px;
    }
    #container {
      display: flex;
      flex-direction: row;
    }
    #chartColumn {
      margin-right: 20px;
      position: relative;
    }
    #rolesColumn {
      flex: 0 0 320px;
      margin-right: 20px;
      white-space: nowrap;
      overflow-x: auto;
    }
    #usersColumn {
      flex: 0 0 400px;
      white-space: nowrap;
      overflow-x: auto;
    }
    .roleListItem {
      margin: 4px 0;
      cursor: pointer;
    }
    .roleListItem:hover {
      background-color: rgba(0,0,0,0.1);
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
    #roleHoverBox {
      margin-top: 10px;
      padding: 5px;
      border: 1px solid #ccc;
      background: #fafafa;
      font-size: 14px;
      white-space: pre-line;
      min-height: 200px;
    }
  </style>
</head>
<body>

<h2>Above-Avg Users (~AVGCOUNT~) — Circles sized by totalResourceCount, Pie slices by role</h2>
<p>
Hover over a circle => show all roles for that user.<br/>
Hover over a role => highlight those slices in all circles, outline circles that contain it.
</p>

<div id="container">
  <div id="chartColumn">
    <div id="chart"></div>
  </div>
  <div id="rolesColumn">
    <h3>All Roles (Filtered Users)</h3>
    <div id="roleItems"></div>
  </div>
  <div id="usersColumn">
    <h3>Users with this Role</h3>
    <div id="roleHoverBox"></div>
  </div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
const userData = {filtered_json};

const allRolesMap = new Map();
const roleUserMap = new Map();

userData.forEach(u => {
  u.roles.forEach(r => {
    const prev = allRolesMap.get(r.roleName) || 0;
    allRolesMap.set(r.roleName, prev + r.count);

    if (!roleUserMap.has(r.roleName)) {
      roleUserMap.set(r.roleName, []);
    }
    roleUserMap.get(r.roleName).push({
      userName: u.userName,
      jobTitle: u.jobTitle,
      roleCount: r.count
    });
  });
});

const allRoles = Array.from(allRolesMap.entries())
  .sort((a,b) => d3.descending(a[1], b[1]))
  .map(([roleName, totalCount]) => { return { roleName, totalCount }; });

const width = 3000;
const height = 2000;
const svg = d3.select("#chart")
  .append("svg")
  .attr("width", 1500)
  .attr("height", 1000)
  .attr("viewBox",[0,0,width,height]);

const tooltip = d3.select("#tooltip");
const roleHoverBox = d3.select("#roleHoverBox");

const maxResources = d3.max(userData, d => d.totalResourceCount) || 1;
const radiusScale = d3.scaleSqrt()
  .domain([0, maxResources])
  .range([0, 160]);

const roleNames = allRoles.map(r => r.roleName);
const colorScale = d3.scaleOrdinal()
  .domain(roleNames)
  .range(d3.quantize(d3.interpolateRainbow, roleNames.length + 1));

// Create node array
let nodes = userData.map((u, i) => {
  const roleSet = new Set(u.roles.map(rr => rr.roleName));
  return {
    index: i,
    user: u,
    userRoles: roleSet,
    x: Math.random()*width,
    y: Math.random()*height,
    r: radiusScale(u.totalResourceCount)
  };
});

const userGroups = svg.selectAll(".userGroup")
  .data(nodes)
  .enter()
  .append("g")
  .attr("class","userGroup");

// Draw pie slices
userGroups.each(function(nd) {
  const g = d3.select(this);
  const user = nd.user;
  const userRadius = nd.r;
  const rolesArr = user.roles;

  const pie = d3.pie().sort(null).value(rr => rr.count);
  const arcsData = pie(rolesArr);
  const arcGen = d3.arc().innerRadius(0).outerRadius(userRadius);

  g.selectAll(".slice")
    .data(arcsData)
    .enter()
    .append("path")
    .attr("class","slice")
    .attr("d", arcGen)
    .attr("fill", d => colorScale(d.data.roleName))
    .attr("stroke","#333")
    .attr("stroke-width",0.5);
});

// Outline circle for highlight
userGroups.append("circle")
  .attr("class","userOutline")
  .attr("r", d => d.r)
  .attr("fill","none")
  .attr("stroke","none")
  .attr("stroke-width",0);

// Add text with userName in center
userGroups.append("text")
  .attr("text-anchor","middle")
  .attr("dy","0.4em")
  .text(d => d.user.userName)
  .each(function(d) {
    const textEl = d3.select(this);
    let fontSize = 50;
    textEl.style("font-size", fontSize+"px");
    while(true) {
      const bbox = textEl.node().getBBox();
      const maxDim = Math.max(bbox.width,bbox.height);
      if(maxDim <= 2*d.r || fontSize<=1) break;
      fontSize--;
      textEl.style("font-size", fontSize+"px");
    }
  });

// Group-level hover => show all roles in tooltip
userGroups
  .on("mouseover", function(evt, nd) {
    tooltip.style("opacity",1);
    const user = nd.user;
    const lines = user.roles.map(r => `(${r.count}) ${r.roleName}`).join("<br/>");
    const html = `
      <div><strong>User:</strong> ${user.userName}</div>
      <div><strong>Total Count:</strong> ${user.totalResourceCount}</div>
      <div><strong>All Roles:</strong><br/>${lines}</div>
    `;
    tooltip.html(html);
  })
  .on("mousemove", function(evt) {
    tooltip
      .style("left",(evt.pageX+10)+"px")
      .style("top",(evt.pageY+10)+"px");
  })
  .on("mouseout", function() {
    tooltip.style("opacity",0);
  });

// Force simulation
const simulation = d3.forceSimulation(nodes)
  .force("center", d3.forceCenter(width/2, height/2))
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
    userGroups.attr("transform", d => `translate(${d.x},${d.y})`);
  });

// Build role list in side column
const roleContainer = d3.select("#roleItems");
roleContainer.selectAll(".roleListItem")
  .data(allRoles)
  .enter()
  .append("div")
  .attr("class","roleListItem")
  .style("border-left", d => `10px solid ${colorScale(d.roleName)}`)
  .text(d => d.totalCount+" - "+d.roleName)
  .on("mouseover", function(evt,d) {
    const roleName = d.roleName;
    svg.selectAll(".slice")
      .transition().duration(100)
      .style("opacity", sliceDatum => {
        return (sliceDatum.data.roleName===roleName)? 1 : 0.15;
      });
    userGroups.select(".userOutline")
      .transition().duration(100)
      .attr("stroke", nd => nd.userRoles.has(roleName)? "black":"none")
      .attr("stroke-width", nd => nd.userRoles.has(roleName)? 2:0);

    const userList = roleUserMap.get(roleName) || [];
    userList.sort((a,b) => b.roleCount - a.roleCount);
    const lines = userList.map(u => `(${u.roleCount}) ${u.userName} | ${u.jobTitle}`);
    d3.select("#roleHoverBox").html(lines.join("\n"));
  })
  .on("mouseout", function() {
    svg.selectAll(".slice")
      .transition().duration(100)
      .style("opacity",1);
    userGroups.select(".userOutline")
      .transition().duration(100)
      .attr("stroke","none")
      .attr("stroke-width",0);
    d3.select("#roleHoverBox").html("");
  });

</script>
</body>
</html>
"""

    final_html = html_template.replace("~AVGCOUNT~", f"{avg:.1f}")
    final_html = final_html.replace("{filtered_json}", filtered_json)

    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"[INFO] Wrote => {out_html} ({len(filtered)} users above ~{avg:.1f} avg).")

def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "output/i_combined_user_identities.json"

    if not os.path.exists(input_file):
        print(f"[ERROR] {input_file} not found.")
        sys.exit(1)

    user_data = load_users_and_merge_principals(input_file)
    if not user_data:
        print("[WARN] No user data.")
        return

    generate_above_avg_html(user_data, "output/l_bubble_chart_users.html")
    print("[INFO] Done! Open 'output/l_bubble_chart_users.html' in your browser.")

if __name__ == "__main__":
    main()
