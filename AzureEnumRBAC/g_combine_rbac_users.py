#!/usr/bin/env python3
"""
g_combine_rbac_users.py

This script combines RBAC assignments for users from multiple sources:
  - User assignments from:
      output/e_assignments/<subscriptionID>/user.json
  - Group assignments: For groups assigned roles in
      output/e_assignments/<subscriptionID>/group.json,
    the script looks up the expanded membership from:
      output/f_ennumerate_group_members/<subscriptionID>_group_members.json
    and applies the group's role assignment to every user member.
    
In addition, the script loads resource count information from:
      output/c_resources/<subscription_id>_resources.json

For each assignment, the script computes a resource count as follows:
  - If the assignment scope is "/" (or equals "/subscriptions/<sub_id>"),
    then the total resource count from the subscription is used.
  - Otherwise, if the scope matches a resource group ID from the resource file,
    that resource group's count is used.
  - Otherwise, the scope is assumed to be an individual resource (count = 1).

The combined data is then transformed into a nested structure whose keys embed the
resource counts in square brackets as follows:

    [<principal_total>]<principleid>
        [<role_total>]<rolename>
            [<leaf_count>]<subscription> : <scope>

That is, at the leaf level the key contains the count and the subscription (the part before
the colon in the original leaf key), and the value is the scope string. All child counts add
up to their parent item's count.

Output is written to:
    output/g_combined_rbac_users.json
"""

import os
import sys
import json

def get_resource_count_for_scope(scope, sub_id, resource_lookup):
    """
    Given a scope string, subscription ID, and a resource lookup dictionary,
    return the resource count for that scope.
    
    - If scope is "/" or equals "/subscriptions/<sub_id>" (case-insensitively),
      return the total resource count.
    - Otherwise, if scope is found in resource_lookup["rg"], return that count;
    - Otherwise, assume it represents an individual resource (count = 1).
    """
    if not resource_lookup:
        return 1
    sub_scope = f"/subscriptions/{sub_id}".lower()
    if scope.strip() == "/" or scope.lower() == sub_scope:
        return resource_lookup.get("total", 0)
    else:
        rg_counts = resource_lookup.get("rg", {})
        return rg_counts.get(scope, 1)

def add_assignment(combined, principal_id, role, scope, sub_id, resource_lookup):
    """
    Adds an assignment to the combined dictionary.
    Grouping is done as:
       combined[principal_id][role][ "<subscription>:<scope>" ]
    where the value is the aggregated resource count.
    """
    resource_count = get_resource_count_for_scope(scope, sub_id, resource_lookup)
    leaf_key = f"{sub_id}:{scope}"
    if principal_id not in combined:
        combined[principal_id] = {}
    if role not in combined[principal_id]:
        combined[principal_id][role] = {}
    if leaf_key not in combined[principal_id][role]:
        combined[principal_id][role][leaf_key] = 0
    combined[principal_id][role][leaf_key] += resource_count

def process_user_assignments(sub_id, combined, resource_lookup):
    """
    Processes the user assignments from:
       output/e_assignments/<subscriptionID>/user.json
    """
    user_file = os.path.join("output", "e_assignments", sub_id, "user.json")
    if not os.path.exists(user_file):
        return
    try:
        with open(user_file, "r", encoding="utf-8") as f:
            user_assignments = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {user_file}: {e}")
        return
    for assignment in user_assignments.values():
        principal_id = assignment.get("principalId")
        role = assignment.get("roleDefinitionName")
        scope = assignment.get("scope")
        add_assignment(combined, principal_id, role, scope, sub_id, resource_lookup)

def process_group_assignments(sub_id, combined, resource_lookup):
    """
    Processes group assignments by combining data from:
       output/e_assignments/<subscriptionID>/group.json
    and
       output/f_ennumerate_group_members/<subscriptionID>_group_members.json

    For each group assignment, each user in the expanded membership gets the
    group's roleDefinitionName and scope.
    """
    group_file = os.path.join("output", "e_assignments", sub_id, "group.json")
    group_members_file = os.path.join("output", "f_ennumerate_group_members", f"{sub_id}_group_members.json")
    if not os.path.exists(group_file) or not os.path.exists(group_members_file):
        return
    try:
        with open(group_file, "r", encoding="utf-8") as f:
            group_assignments = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {group_file}: {e}")
        return
    try:
        with open(group_members_file, "r", encoding="utf-8") as f:
            group_members = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {group_members_file}: {e}")
        return
    for group_id, assignment in group_assignments.items():
        role = assignment.get("roleDefinitionName")
        scope = assignment.get("scope")
        # For each group assignment, apply its role/scope to every user in the expanded membership.
        if group_id in group_members:
            members_info = group_members[group_id].get("members", {})
            users = members_info.get("users", [])
            for user in users:
                add_assignment(combined, user, role, scope, sub_id, resource_lookup)

def load_resource_lookup(sub_id):
    """
    For a given subscription, load the resource data from:
       output/c_resources/<subscription_id>_resources.json
    and build a lookup dictionary:
       {
         "total": <total resource count>,
         "rg": { <resourceGroupID>: <resourceCount>, ... }
       }
    If the file does not exist or cannot be parsed, returns an empty dict.
    """
    res_file = os.path.join("output", "c_resources", f"{sub_id}_resources.json")
    if not os.path.exists(res_file):
        return {}
    try:
        with open(res_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load resource file {res_file}: {e}")
        return {}
    lookup = {}
    lookup["total"] = data.get("resourceCount", 0)
    rg_lookup = {}
    for rg in data.get("resourceGroups", []):
        rg_id = rg.get("id")
        if rg_id:
            rg_lookup[rg_id] = rg.get("resourceCount", 0)
    lookup["rg"] = rg_lookup
    return lookup

def transform_structure(combined):
    """
    Transforms the combined structure into a new nested structure where
    each key is prefixed with its aggregated resource count in square brackets.
    
    Desired structure:
    {
       "[<principal_total>]<principleid>": {
             "[<role_total>]<rolename>": {
                   "[<leaf_count>]<subscription>" : "<scope>",
                   ...
             },
             ...
       },
       ...
    }
    Here:
      - <leaf_count> is the count for that subscription:scope assignment.
      - <role_total> is the sum of counts for all leaf entries under that role.
      - <principal_total> is the sum of counts for all roles for that principal.
    At the leaf level, we split the original key (which is "<sub_id>:<scope>")
    so that the key becomes "[<leaf_count>]<sub_id>" and the value is "<scope>".
    """
    transformed = {}
    for principal, roles in combined.items():
        principal_total = 0
        new_roles = {}
        for role, leaves in roles.items():
            role_total = sum(leaves.values())
            principal_total += role_total
            new_leaves = {}
            for leaf, count in leaves.items():
                # Split leaf into subscription and scope (expected format: "<sub_id>:<scope>")
                if ":" in leaf:
                    sub_part, scope_part = leaf.split(":", 1)
                else:
                    sub_part, scope_part = leaf, ""
                new_leaf_key = f"[{count}]{sub_part}"
                new_leaves[new_leaf_key] = scope_part
            new_role_key = f"[{role_total}]{role}"
            new_roles[new_role_key] = new_leaves
        new_principal_key = f"[{principal_total}]{principal}"
        transformed[new_principal_key] = new_roles
    return transformed

def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    combined = {}

    # Load subscriptions from output/b_subscriptions.json.
    subscriptions_file = os.path.join("output", "b_subscriptions.json")
    if not os.path.exists(subscriptions_file):
        print(f"[ERROR] Subscriptions file not found: {subscriptions_file}")
        sys.exit(1)
    try:
        with open(subscriptions_file, "r", encoding="utf-8") as f:
            subscriptions = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load subscriptions: {e}")
        sys.exit(1)

    # Process assignments for each subscription.
    for sub in subscriptions:
        sub_id = sub.get("id")
        if not sub_id:
            continue
        print(f"[INFO] Processing subscription {sub_id} ...")
        resource_lookup = load_resource_lookup(sub_id)
        process_user_assignments(sub_id, combined, resource_lookup)
        process_group_assignments(sub_id, combined, resource_lookup)
        # (ServicePrincipal assignments are not processed in this RBAC user combination.)
    
    # Transform the combined structure to include counts in the key names,
    # and adjust leaf-level entries as desired.
    transformed = transform_structure(combined)
    
    # Write the transformed output.
    output_file = os.path.join(output_dir, "g_combined_rbac_users.json")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transformed, f, indent=2)
        print(f"[INFO] Combined RBAC users written to {output_file}")
    except Exception as e:
        print(f"[ERROR] Failed to write output: {e}")

if __name__ == "__main__":
    main()
