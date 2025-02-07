#!/usr/bin/env python3
"""
i_combine_identities.py

Reads two inputs:
  1) h_user_personal_data.json (keyed by user ID; Graph profile info)
  2) g_combined_rbac_users.json (keyed by bracketed principal IDs, e.g. "[12]xxxx-...")

For each user:
  - Groups them under "<givenName> <surname>" (or fallback if empty).
  - Includes fields (mail, displayName, jobTitle, mobilePhone).
  - Applies custom logic to businessPhones:
      * Omit if None or empty
      * If exactly one element, store as "businessPhone" (string)
      * If multiple elements, store as "businessPhones" (list)
  - Adds an "rbac" property with the RBAC structure from g_combined_rbac_users.json
    corresponding to that user ID (if any).

Any fields whose values are None are omitted entirely, so null values don't appear.
"""

import os
import sys
import json

INPUT_H_FILE  = os.path.join("output", "h_user_personal_data.json")
INPUT_G_FILE  = os.path.join("output", "g_combined_rbac_users.json")
OUTPUT_FILE   = os.path.join("output", "i_combined_user_identities.json")

def extract_id_from_bracketed_key(key: str) -> str:
    """
    If the key is something like "[12]00000000-aaaa-bbbb-cccc-ffffffffffff",
    return the substring after the first ']' (the real user ID).
    If no bracket is found, return the string as-is.
    """
    idx = key.find(']')
    if idx != -1:
        return key[idx+1:]
    return key

def main():
    # 1. Check for input files
    if not os.path.exists(INPUT_H_FILE):
        print(f"[ERROR] Expected h-phase file not found: {INPUT_H_FILE}")
        sys.exit(1)
    if not os.path.exists(INPUT_G_FILE):
        print(f"[ERROR] Expected g-phase file not found: {INPUT_G_FILE}")
        sys.exit(1)

    # 2. Load user data from h_user_personal_data.json
    try:
        with open(INPUT_H_FILE, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {INPUT_H_FILE}: {e}")
        sys.exit(1)

    # 3. Load and transform g_combined_rbac_users.json
    #    We build a lookup table keyed by the "real" user ID
    #    (extracted from bracket-laden keys).
    rbac_data_by_id = {}
    try:
        with open(INPUT_G_FILE, "r", encoding="utf-8") as f:
            rbac_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load {INPUT_G_FILE}: {e}")
        sys.exit(1)

    for bracketed_key, rbac_object in rbac_data.items():
        real_id = extract_id_from_bracketed_key(bracketed_key)
        rbac_data_by_id[real_id] = rbac_object

    # 4. Build the combined data structure
    combined_identities = {}

    for user_id, details in user_data.items():
        # a) Determine the top-level name
        given_name = details.get("givenName") or ""
        surname    = details.get("surname") or ""
        pieces = [n.strip() for n in (given_name, surname) if n.strip()]
        if pieces:
            full_name = " ".join(pieces)
        else:
            # fallback
            full_name = details.get("displayName") or details.get("userPrincipalName") or "(Unknown)"

        # b) Prepare user entry with standard fields
        user_entry = {}
        for field in ["mail", "displayName", "jobTitle", "mobilePhone"]:
            val = details.get(field)
            if val is not None:
                user_entry[field] = val

        # c) BusinessPhones logic
        phone_list = details.get("businessPhones")
        if phone_list is not None:
            if len(phone_list) == 1:
                user_entry["businessPhone"] = phone_list[0]
            elif len(phone_list) > 1:
                user_entry["businessPhones"] = phone_list
            # omit if empty

        # d) Attach the RBAC data if found
        found_rbac = rbac_data_by_id.get(user_id)
        if found_rbac is not None:
            user_entry["rbac"] = found_rbac

        # e) Insert into combined structure
        if full_name not in combined_identities:
            combined_identities[full_name] = {}
        combined_identities[full_name][user_id] = user_entry

    # 5. Write out the combined data
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_identities, f, indent=2)
        print(f"[INFO] Successfully wrote combined identities to {OUTPUT_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to write {OUTPUT_FILE}: {e}")

if __name__ == "__main__":
    main()
