#!/usr/bin/env python3
"""
j_role_matrix.py

Generates a CSV (j_role_matrix.csv) with columns:
  principle_count, role, name, displayName, jobTitle, principalID, scope

Where:
- principle_count: total times that 'role' appears across the entire data set (all users, principals, sub-scopes).
- role: label parsed from bracketed role keys, e.g. "[6]Contributor" -> "Contributor".
- name: the top-level user key in i_combined_user_identities.json.
- displayName: from the principal's "displayName".
- jobTitle: from the principal's "jobTitle".
- principalID: the dictionary key for that principal ID.
- scope: the subscription/resource string from each sub-scope.

Usage:
  python j_role_matrix.py [optional_input_file] [optional_output_csv]

Defaults:
  - Input:  output/i_combined_user_identities.json
  - Output: output/j_role_matrix.csv
"""

import os
import sys
import json
import csv

def parse_bracketed_label(s: str) -> str:
    """
    Given '[6]Contributor', returns 'Contributor'.
    If no bracket, return s as-is.
    """
    if not s.startswith("[") or "]" not in s:
        return s
    return s[s.index("]") + 1:].strip()

def main():
    # Default file paths
    default_input  = os.path.join("output", "i_combined_user_identities.json")
    default_output = os.path.join("output", "j_role_matrix.csv")

    # Optional command-line arguments
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        input_file = default_input

    if len(sys.argv) >= 3:
        output_csv = sys.argv[2]
    else:
        output_csv = default_output

    # Check input existence
    if not os.path.exists(input_file):
        print(f"[ERROR] Input file not found: {input_file}")
        sys.exit(1)

    # Load JSON
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read JSON from {input_file}: {e}")
        sys.exit(1)

    # Ensure output directory
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # We'll do two passes:
    # Pass A: gather rows + count how many times each role appears globally.
    # Pass B: fill 'principle_count' for each row from that global map.

    rows = []
    role_count_map = {}

    # ============= PASS A: build row data + track role frequency =============
    # data structure:
    # {
    #   "User Name": {
    #       "PrincipalID": {
    #           "displayName": "...",
    #           "jobTitle": "...",
    #           "rbac": {
    #             "[6]Contributor": { "[6]subId": "/subscriptions/...", ... },
    #             ...
    #           }
    #       },
    #       ...
    #   },
    #   ...
    # }

    for name, principal_map in data.items():
        for principal_id, details in principal_map.items():
            display_name = details.get("displayName", "")
            job_title    = details.get("jobTitle", "")
            rbac_obj     = details.get("rbac", {})

            if not isinstance(rbac_obj, dict):
                continue

            # For each bracketed role key
            for role_key, sub_scopes_dict in rbac_obj.items():
                role_label = parse_bracketed_label(role_key)
                if not isinstance(sub_scopes_dict, dict):
                    continue

                # sub_scopes_dict => { "[xxx]someSubId": "/subscriptions/...", ... }
                for _scope_bracket, scope_value in sub_scopes_dict.items():
                    # increment global role count
                    role_count_map[role_label] = role_count_map.get(role_label, 0) + 1

                    # store row (we'll fill principle_count later)
                    rows.append({
                        "role": role_label,
                        "name": name,
                        "displayName": display_name,
                        "jobTitle": job_title,
                        "principalID": principal_id,
                        "scope": scope_value
                    })

    # ============= PASS B: fill principle_count =============
    for row in rows:
        row["principle_count"] = role_count_map[row["role"]]

    # ============= Write CSV =============
    fieldnames = [
        "principle_count",
        "role",
        "name",
        "displayName",
        "jobTitle",
        "principalID",
        "scope"
    ]

    try:
        with open(output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            row_count = 0
            for row in rows:
                writer.writerow({
                    "principle_count": row["principle_count"],
                    "role": row["role"],
                    "name": row["name"],
                    "displayName": row["displayName"],
                    "jobTitle": row["jobTitle"],
                    "principalID": row["principalID"],
                    "scope": row["scope"]
                })
                row_count += 1
        print(f"[INFO] Wrote {row_count} rows to {output_csv}")
    except Exception as e:
        print(f"[ERROR] Could not write to {output_csv}: {e}")

if __name__ == "__main__":
    main()
