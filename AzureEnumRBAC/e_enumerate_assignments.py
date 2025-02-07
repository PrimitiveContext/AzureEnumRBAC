#!/usr/bin/env python3
"""
e_enumerate_assignments.py

Enumerates all Azure role assignments for each subscription (subscription scope,
resource group scope, resource scope) and separates results by principalType
(User, Group, ServicePrincipal, etc.).

Outputs per subscription in:
  output/e_assignments/<subId>/
    - users.json
    - groups.json
    - serviceprincipals.json
    - foreigngroups.json
    - etc.

Uses a single TQDM progress bar without mid-run prints (only before/after).
"""

import os
import sys
import json
from tqdm import tqdm

from helpers import run_az_cli_command

SUBSCRIPTIONS_FILE = os.path.join("output", "b_subscriptions.json")
BASE_OUTPUT_DIR   = os.path.join("output", "e_assignments")

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def sanitize_filename(s: str) -> str:
    """Make a string safe for filenames by removing/transforming characters as needed."""
    return "".join(char.lower() for char in s if char.isalnum())

def main():
    # Print only before progress bar starts
    print("[INFO] Enumerating role assignments across all subscriptions...")

    ensure_dir_exists(BASE_OUTPUT_DIR)

    # 1. Read subscriptions from b_subscriptions.json
    try:
        with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            subscriptions = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {SUBSCRIPTIONS_FILE}. Did you run b_get_subscriptions.py?")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON in: {SUBSCRIPTIONS_FILE}.")
        sys.exit(1)

    # We'll collect the total # of assignments processed across all subscriptions
    total_assignments = 0

    # Create a TQDM progress bar with initial total=0 (we'll expand it dynamically)
    with tqdm(total=0, desc="Role Assignments", unit="ra") as pbar:
        # 2. Loop over each subscription
        for sub in subscriptions:
            sub_id = sub.get("id")
            if not sub_id:
                continue

            # Run CLI to get role assignments at subscription scope
            cmd = f"az role assignment list --subscription {sub_id} --all -o json"
            try:
                role_assignments = run_az_cli_command(cmd)
            except Exception as e:
                # If an error, just skip this subscription
                continue

            # Expand the progress bar's total by the count for this subscription
            pbar.total += len(role_assignments)
            pbar.refresh()

            # Build a dict { principalType => list of assignments }
            assignments_by_type = {}
            for ra in role_assignments:
                p_type = ra.get("principalType", "Unknown") or "Unknown"
                assignments_by_type.setdefault(p_type, []).append(ra)

                # Each assignment increments the progress
                pbar.update(1)
                total_assignments += 1

            # Write out one JSON file per principalType
            sub_output_dir = os.path.join(BASE_OUTPUT_DIR, sub_id)
            ensure_dir_exists(sub_output_dir)
            for p_type, assignments in assignments_by_type.items():
                # Convert to dict keyed by principalId
                assignments_dict = {}
                for assignment in assignments:
                    principal_id = assignment.get("principalId")
                    if principal_id:
                        assignments_dict[principal_id] = assignment

                fname_part = sanitize_filename(p_type)
                out_file = os.path.join(sub_output_dir, f"{fname_part}.json")
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(assignments_dict, f, indent=2)

    # After progress bar is complete
    print(f"[INFO] Finished enumerating role assignments by principalType. "
          f"Total role assignments processed: {total_assignments}")

if __name__ == "__main__":
    main()
