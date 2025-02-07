#!/usr/bin/env python3

"""
c_enumerate_resources.py

Reads the output from b_subscriptions.json and enumerates all resource groups
and resources in each subscription. Outputs a detailed JSON file per subscription
with total resource count, resource group count, and for each resource group,
a list of resource IDs only.

A single TQDM progress bar is used to track progress across all subscriptions,
and no output is printed while the bar is running, to avoid breaking the progress display.
"""

import json
import os
import sys

from tqdm import tqdm
from helpers import run_az_cli_command

OUTPUT_DIR = os.path.join("output", "c_resources")
SUBSCRIPTIONS_FILE = os.path.join("output", "b_subscriptions.json")

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def main():
    # Make sure the output directory exists
    ensure_output_dir_exists()

    # 1. Read all subscriptions from b_subscriptions.json
    try:
        with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            subscriptions = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Cannot find {SUBSCRIPTIONS_FILE}. Did you run b_get_subscriptions.py?")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse JSON in {SUBSCRIPTIONS_FILE}.")
        sys.exit(1)

    # We'll store final messages to print AFTER the progress bar completes
    final_messages = []

    # Create a TQDM progress bar for the total number of subscriptions
    total_subs = len(subscriptions)
    with tqdm(total=total_subs, desc="Enumerating resources", unit="sub") as pbar:
        for sub in subscriptions:
            sub_id = sub.get("id")
            sub_name = sub.get("name")

            if not sub_id:
                # We'll record a warning but not print now
                final_messages.append("[WARNING] Subscription missing 'id' field. Skipping.")
                pbar.update(1)
                continue

            # 2. Get all resource groups in this subscription
            cmd_rg = f"az group list --subscription {sub_id} -o json"
            rgs_data = run_az_cli_command(cmd_rg)

            # Create a dict of { rgName: {...info..., "resources": []} }
            resource_groups = {}
            for rg in rgs_data:
                rg_name = rg.get("name")
                if rg_name:
                    resource_groups[rg_name] = {
                        "id": rg.get("id"),
                        "location": rg.get("location"),
                        "tags": rg.get("tags", {}),
                        "resources": []
                    }

            # 3. Get all resources in this subscription
            cmd_res = f"az resource list --subscription {sub_id} -o json"
            resources_data = run_az_cli_command(cmd_res)

            # Group resources by RG, storing only resource IDs
            for res in resources_data:
                rg_name = res.get("resourceGroup")
                if rg_name and rg_name in resource_groups:
                    resource_groups[rg_name]["resources"].append(res["id"])

            # Calculate totals
            total_resources = sum(len(rg_info["resources"]) for rg_info in resource_groups.values())
            total_rg_count = len(resource_groups)

            # Build a list representation for the JSON output
            rg_list_output = []
            for rg_name, rg_info in resource_groups.items():
                rg_list_output.append({
                    "resourceGroupName": rg_name,
                    "id": rg_info["id"],
                    "location": rg_info["location"],
                    "tags": rg_info["tags"],
                    "resourceCount": len(rg_info["resources"]),
                    "resources": rg_info["resources"]
                })

            # Final JSON structure for this subscription
            subscription_output = {
                "subscriptionId": sub_id,
                "subscriptionName": sub_name,
                "resourceGroupCount": total_rg_count,
                "resourceCount": total_resources,
                "resourceGroups": rg_list_output
            }

            # 4. Write out one file per subscription
            out_filename = f"{sub_id}_resources.json"
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(subscription_output, f, indent=2)

            # We'll record a final message for this subscription
            final_messages.append(
                f"Subscription '{sub_name}' ({sub_id}): created file => {out_path} "
                f"[RGs={total_rg_count}, Resources={total_resources}]"
            )

            # Update progress bar by 1 for this subscription
            pbar.update(1)

    # AFTER the progress bar completes, we can safely print final messages
    print("\n[INFO] c_enumerate_resources summary:")
    for msg in final_messages:
        print("  " + msg)

if __name__ == "__main__":
    main()
