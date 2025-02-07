#!/usr/bin/env python3
"""
k_user_matrix.py

Generates k_user_matrix.csv with columns:
  name, displayName, jobTitle, principalID, role, scope, resource_count, resource_path

Omits any row where resource_count = 0.

Steps:
1) Parse the c_resources/*.json files => sub_map:
     {
       "<subId>.lower()": {
         "subscriptionId": "<subId>",
         "resourceGroups": {
           "<rgId>.lower()": {
              "id": "<rgId>",
              "resourceGroupName": "...",
              "resourceCount": <int>
           },
           ...
         },
         "total": <int>  # total resourceCount for sub
       },
       ...
     }

2) Parse i_combined_user_identities.json => for each user+principal => each bracketed role => each sub-scope.

3) If scope = subscription => produce row(s) for each RG w/ nonzero resourceCount
   If scope = RG => produce row if that RG resourceCount>0
   Else => treat as a single resource => resource_count=1 (unless you want to handle that differently).
   Skip rows where resource_count=0.

Output:
  output/k_user_matrix.csv
"""

import os
import sys
import json
import csv
import glob

def load_c_resources(c_resources_dir="output/c_resources"):
    """
    Loads all <subId>_resources.json files in c_resources_dir.
    Returns sub_map: { subId.lower(): { "subscriptionId":..., "resourceGroups":..., "total": int } }
    """
    sub_map = {}
    path_pattern = os.path.join(c_resources_dir, "*_resources.json")
    for path in glob.glob(path_pattern):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {path}: {e}")
            continue

        sub_id = data.get("subscriptionId")
        if not sub_id:
            print(f"[WARN] No subscriptionId in {path}, skipping.")
            continue

        resource_groups_data = data.get("resourceGroups", [])
        rg_map = {}
        for rg_info in resource_groups_data:
            rg_id = rg_info.get("id")  # e.g. "/subscriptions/.../resourceGroups/..."
            if rg_id:
                rg_map[rg_id.lower()] = {
                    "id": rg_id,
                    "resourceGroupName": rg_info.get("resourceGroupName"),
                    "resourceCount": rg_info.get("resourceCount", 0)
                }

        sub_map[sub_id.lower()] = {
            "subscriptionId": sub_id,
            "resourceGroups": rg_map,
            "total": data.get("resourceCount", 0)
        }
    return sub_map

def parse_bracketed_label(s: str) -> str:
    """E.g. "[6]Contributor" -> "Contributor". If no bracket, return s as-is."""
    if not s.startswith("[") or "]" not in s:
        return s
    return s[s.index("]")+1:].strip()

def is_subscription_scope(scope: str, sub_id: str) -> bool:
    """True if scope is "/" or "/subscriptions/<sub_id>" (case-insensitive)."""
    if not scope or not sub_id:
        return False
    s_lower = scope.strip().lower()
    sub_lower = f"/subscriptions/{sub_id}".lower()
    return (s_lower == "/" or s_lower == sub_lower)

def main():
    default_i_combined = os.path.join("output", "i_combined_user_identities.json")
    c_resources_dir = os.path.join("output", "c_resources")
    output_csv = os.path.join("output", "k_user_matrix.csv")

    if len(sys.argv) > 1:
        i_combined_path = sys.argv[1]
    else:
        i_combined_path = default_i_combined

    # 1) load c_resources
    sub_map = load_c_resources(c_resources_dir)

    # 2) load i_combined_user_identities.json
    if not os.path.exists(i_combined_path):
        print(f"[ERROR] {i_combined_path} not found.")
        sys.exit(1)

    try:
        with open(i_combined_path, "r", encoding="utf-8") as f:
            i_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not load JSON from {i_combined_path}: {e}")
        sys.exit(1)

    # 3) write CSV
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    fieldnames = [
        "name",
        "displayName",
        "jobTitle",
        "principalID",
        "role",
        "scope",
        "resource_count",
        "resource_path"
    ]
    try:
        out_f = open(output_csv, "w", encoding="utf-8", newline="")
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
    except Exception as e:
        print(f"[ERROR] Could not open {output_csv} for writing: {e}")
        sys.exit(1)

    row_count = 0

    # 4) For each user => principal => role => sub-scope => determine resource_count + resource_path
    for name, principal_map in i_data.items():
        for principal_id, details in principal_map.items():
            display_name = details.get("displayName", "")
            job_title    = details.get("jobTitle", "")
            rbac_obj     = details.get("rbac", {})
            if not isinstance(rbac_obj, dict):
                continue

            for role_bracket_key, sub_scopes_dict in rbac_obj.items():
                role_label = parse_bracketed_label(role_bracket_key)
                if not isinstance(sub_scopes_dict, dict):
                    continue

                for _sc_br_key, scope_str in sub_scopes_dict.items():
                    scope_str = scope_str.strip()
                    # figure out subId if scope starts with "/subscriptions/"
                    parts = scope_str.lower().split("/")
                    sub_id_candidate = None
                    if len(parts) > 2 and parts[1] == "subscriptions":
                        sub_id_candidate = parts[2]

                    rows_to_write = []  # we might expand multiple RGs if subscription-level

                    if sub_id_candidate and sub_id_candidate in sub_map:
                        sub_info = sub_map[sub_id_candidate]
                        if is_subscription_scope(scope_str, sub_id_candidate):
                            # expand all resource groups with resourceCount>0
                            for rg_id_lower, rg_data in sub_info["resourceGroups"].items():
                                rc = rg_data["resourceCount"]
                                if rc == 0:
                                    continue  # skip resource_count=0
                                rows_to_write.append({
                                    "name": name,
                                    "displayName": display_name,
                                    "jobTitle": job_title,
                                    "principalID": principal_id,
                                    "role": role_label,
                                    "scope": scope_str,
                                    "resource_count": rc,
                                    "resource_path": rg_data["id"]
                                })
                        else:
                            # maybe RG or resource
                            scope_lower = scope_str.lower()
                            rg_data = sub_info["resourceGroups"].get(scope_lower)
                            if rg_data:
                                # exact RG
                                rc = rg_data["resourceCount"]
                                if rc > 0:
                                    rows_to_write.append({
                                        "name": name,
                                        "displayName": display_name,
                                        "jobTitle": job_title,
                                        "principalID": principal_id,
                                        "role": role_label,
                                        "scope": scope_str,
                                        "resource_count": rc,
                                        "resource_path": rg_data["id"]
                                    })
                            else:
                                # resource => resource_count=1 unless 0 is possible
                                # Typically a resource wouldn't be "0" unless it's an invalid scope
                                # We'll store as 1
                                rows_to_write.append({
                                    "name": name,
                                    "displayName": display_name,
                                    "jobTitle": job_title,
                                    "principalID": principal_id,
                                    "role": role_label,
                                    "scope": scope_str,
                                    "resource_count": 1,
                                    "resource_path": scope_str
                                })
                    else:
                        # not a known subscription => treat as resource => count=1
                        rows_to_write.append({
                            "name": name,
                            "displayName": display_name,
                            "jobTitle": job_title,
                            "principalID": principal_id,
                            "role": role_label,
                            "scope": scope_str,
                            "resource_count": 1,
                            "resource_path": scope_str
                        })

                    # now write only those with resource_count>0
                    for row in rows_to_write:
                        if row["resource_count"] > 0:
                            writer.writerow(row)
                            row_count += 1

    out_f.close()
    print(f"[INFO] Wrote {row_count} rows to {output_csv}")


if __name__ == "__main__":
    main()
