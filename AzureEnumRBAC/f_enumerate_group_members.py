#!/usr/bin/env python3

import os
import sys
import json
import requests
from tqdm import tqdm
from helpers import get_msgraph_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

OUTPUT_DIR = os.path.join("output", "f_ennumerate_group_members")
ERROR_LOG = os.path.join(OUTPUT_DIR, "f_members_errors.log")

def log_warning_or_error(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as ef:
        ef.write(msg.rstrip() + "\n")

def expand_groups_in_subscription(sub_id, group_ids, access_token):

    sub_data = {}

    with tqdm(total=len(group_ids), desc=f"Groups in {sub_id}", position=1, leave=False) as subbar:
        for g_id in group_ids:
            details = get_group_details(g_id, access_token)
            display_name = details.get("displayName") if details else None

            visited = set()
            members_agg = expand_group_membership(g_id, access_token, visited)
            # Convert sets => sorted lists
            for key in members_agg:
                members_agg[key] = sorted(members_agg[key])

            sub_data[g_id] = {
                "displayName": display_name,
                "members": members_agg
            }

            # Each group done => update sub-bar
            subbar.update(1)

    return sub_data

def expand_group_membership(group_id, access_token, visited):

    if group_id in visited:
        return {"users": set(), "groups": set(), "others": set()}
    visited.add(group_id)

    headers = {"Authorization": f"Bearer {access_token}"}
    aggregated = {"users": set(), "groups": set(), "others": set()}

    url = f"{GRAPH_BASE_URL}/groups/{group_id}/members?$top=999"
    while url:
        try:
            resp = requests.get(url, headers=headers)
        except Exception as ex:
            log_warning_or_error(f"[ERROR] Exception fetching members of {group_id}: {ex}")
            return aggregated
        if not resp.ok:
            log_warning_or_error(f"[WARN] Could not fetch members of {group_id}: {resp.status_code} {resp.text}")
            return aggregated

        data = resp.json()
        members = data.get("value", [])
        for m in members:
            odata_type = m.get("@odata.type", "").lower()
            m_id = m.get("id", "")
            if "user" in odata_type:
                aggregated["users"].add(m_id)
            elif "group" in odata_type:
                aggregated["groups"].add(m_id)
                # recursively expand
                nested = expand_group_membership(m_id, access_token, visited)
                aggregated["users"].update(nested["users"])
                aggregated["groups"].update(nested["groups"])
                aggregated["others"].update(nested["others"])
            else:
                aggregated["others"].add(m_id)

        url = data.get("@odata.nextLink")
    return aggregated

def get_group_details(group_id, access_token):
    url = f"{GRAPH_BASE_URL}/groups/{group_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(url, headers=headers)
    except Exception as ex:
        log_warning_or_error(f"[ERROR] get_group_details for {group_id}: {ex}")
        return None
    if resp.ok:
        return resp.json()
    else:
        log_warning_or_error(f"[WARN] Failed to retrieve group {group_id}: {resp.status_code} {resp.text}")
        return None

def main():
    print("[INFO] Starting membership expansions with nested progress bars...")

    # Prepare output + error log
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Clear error log
    with open(ERROR_LOG, "w", encoding="utf-8") as ef:
        ef.write("Nested TQDM phase errors/warnings:\n")

    # load subscriptions
    subs_file = os.path.join("output", "b_subscriptions.json")
    if not os.path.exists(subs_file):
        with open(ERROR_LOG, "a", encoding="utf-8") as ef:
            ef.write(f"[ERROR] Subscriptions file not found: {subs_file}\n")
        sys.exit(1)
    try:
        with open(subs_file, "r", encoding="utf-8") as f:
            subs = json.load(f)
    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as ef:
            ef.write(f"[ERROR] Failed reading subs: {e}\n")
        sys.exit(1)

    # attempt to get graph token
    try:
        access_token = get_msgraph_token()
    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as ef:
            ef.write(f"[ERROR] get_msgraph_token: {e}\n")
        sys.exit(1)

    base_assign_dir = os.path.join("output", "e_assignments")

    # We'll gather how many subscriptions have group assignments
    # so we can create a main bar with that many steps
    sub_with_groups = []
    for sub in subs:
        sub_id = sub.get("id")
        if not sub_id:
            continue
        g_file = os.path.join(base_assign_dir, sub_id, "group.json")
        if os.path.exists(g_file):
            sub_with_groups.append(sub_id)

    # main bar => # of subscriptions that have group.json
    with tqdm(total=len(sub_with_groups), desc="Subscriptions", unit="sub") as mainbar:
        for sub_id in sub_with_groups:
            # read group assignments
            path = os.path.join(base_assign_dir, sub_id, "group.json")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    group_data = json.load(f)
            except Exception as ex:
                log_warning_or_error(f"[ERROR] read {path}: {ex}")
                # update main bar even if skip
                mainbar.update(1)
                continue

            # group_data => { group_id => { "roleDefinitionName":..., ...}, ... }
            group_ids = list(group_data.keys())

            # expand groups in this subscription
            sub_result = expand_groups_in_subscription(sub_id, group_ids, access_token)

            # write subscription output
            out_file = os.path.join(OUTPUT_DIR, f"{sub_id}_group_members.json")
            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(sub_result, f, indent=2)
            except Exception as ex:
                log_warning_or_error(f"[ERROR] writing {out_file}: {ex}")

            # done this subscription => main bar update
            mainbar.update(1)

    print("[INFO] Nested progress expansions complete. See error log for any issues.")

if __name__ == "__main__":
    main()
