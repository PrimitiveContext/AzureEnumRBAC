#!/usr/bin/env python3
"""
h_get_user_personal_data.py

This script reads the combined RBAC users file (g_combined_rbac_users.json) to obtain all user principal IDs
(which may be bracketed, e.g. "[12]00000000-aaaa-bbbb-cccc-ffffffffffff"). It extracts the real ID and then
uses multithreading in batches of 100 to query Microsoft Graph for each user's personal data.

A TQDM progress bar is displayed to show how many users are processed. No prints occur during
progress bar updates. All diagnostic messages (warnings, batch info, etc.) are collected and
displayed after the progress bar completes.

Output:
    output/h_user_personal_data.json

Prerequisites:
    - g_combined_rbac_users.json must exist in the output folder.
    - The user must be logged in (via az login) so that helpers.get_msgraph_token() returns a valid token.
"""

import os
import sys
import json
import requests
import concurrent.futures
from tqdm import tqdm

# Adjust import if "helpers.py" is in a different directory
from helpers import get_msgraph_token

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

def extract_id_from_bracketed_key(key: str) -> str:
    """
    Given a bracketed key like "[12]00000000-aaaa-bbbb-cccc-ffffffffffff",
    return the substring after the first ']' (i.e. "00000000-aaaa-bbbb-cccc-ffffffffffff").
    If there is no ']' present, return the original string.
    """
    idx = key.find(']')
    if idx != -1:
        return key[idx+1:]
    return key

def get_user_data(user_id, token):
    """
    Queries Microsoft Graph API for the user with the given user_id.
    Returns a tuple (user_id, data, warning_msg).
       - user_id: the user we're querying
       - data: the JSON response from Graph if successful, else None
       - warning_msg: any warning string if something failed, else None
    """
    url = f"{GRAPH_BASE_URL}/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return (user_id, response.json(), None)
        else:
            w = f"Failed to fetch data for user {user_id}: {response.status_code} {response.text}"
            return (user_id, None, w)
    except Exception as e:
        w = f"Exception for user {user_id}: {e}"
        return (user_id, None, w)

def load_existing_output(output_file):
    """
    If the output file exists, load and return its contents as a dict;
    otherwise, return an empty dict.
    """
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            # Return empty if it fails, but keep a note
            return {}
    return {}

def main():
    combined_file = os.path.join("output", "g_combined_rbac_users.json")
    output_file = os.path.join("output", "h_user_personal_data.json")

    # Ensure the combined file exists
    if not os.path.exists(combined_file):
        print(f"[ERROR] Combined RBAC users file not found: {combined_file}")
        sys.exit(1)

    # Load the combined RBAC user data (only need the keys)
    try:
        with open(combined_file, "r", encoding="utf-8") as f:
            combined_data = json.load(f)
        # Convert bracketed principal keys to real AAD user IDs
        all_user_ids = [extract_id_from_bracketed_key(k) for k in combined_data.keys()]
    except Exception as e:
        print(f"[ERROR] Failed to load {combined_file}: {e}")
        sys.exit(1)

    # Load already processed users so we can skip them if we re-run the script
    user_data_dict = load_existing_output(output_file)
    processed_ids = set(user_data_dict.keys())

    # Filter out users that are already processed
    remaining_user_ids = [uid for uid in all_user_ids if uid not in processed_ids]

    total_users = len(all_user_ids)
    remaining_count = len(remaining_user_ids)

    # Print only before progress bar starts
    print(f"[INFO] Total users: {total_users}. Already processed: {len(processed_ids)}. "
          f"Remaining: {remaining_count}.")

    # Get a valid Microsoft Graph access token
    try:
        token = get_msgraph_token()
    except Exception as e:
        print(f"[ERROR] Failed to get MS Graph token: {e}")
        sys.exit(1)

    # We'll collect warnings in a list, to print them after the progress bar finishes
    warnings = []

    # Process users in batches of 100
    batch_size = 100

    # Create a TQDM progress bar that reflects how many users remain to process
    with tqdm(total=remaining_count, desc="Fetching user data", unit="user") as pbar:
        for i in range(0, remaining_count, batch_size):
            batch = remaining_user_ids[i : i + batch_size]

            # Use ThreadPoolExecutor to run requests concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_user = {executor.submit(get_user_data, user_id, token): user_id
                                  for user_id in batch}
                for future in concurrent.futures.as_completed(future_to_user):
                    user_id, data, warn_msg = future.result()
                    if data is not None:
                        user_data_dict[user_id] = data
                    if warn_msg:
                        warnings.append(warn_msg)

            # Update the output file after each batch
            # (No prints here so we don't break the TQDM bar)
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(user_data_dict, f, indent=2)
            except Exception as e:
                warnings.append(f"Failed to update output file after a batch: {e}")

            # Advance progress bar by the batch size (or the actual batch length, which may be less)
            pbar.update(len(batch))

    # After the progress bar is complete, print final info
    print(f"[INFO] Completed processing all users. Total user records: {len(user_data_dict)}")

    # Print any warnings we accumulated
    if warnings:
        print("[INFO] The following warnings occurred during execution:")
        for w in warnings:
            print(f"  - {w}")

if __name__ == "__main__":
    main()
