#!/usr/bin/env python3
"""
b_get_subscriptions.py

Retrieves all subscriptions accessible by the logged-in Azure user
and removes user data from the output. Stores them as JSON in
'output/b_subscriptions.json'.
"""

import os
import json
import sys

# Adjust import if "helpers.py" is in a different directory
from helpers import run_az_cli_command

OUTPUT_FILE = "output/b_subscriptions.json"

def main():
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    print("[INFO] Retrieving Azure subscriptions...")

    # Call Azure CLI to get all subscriptions
    subscriptions = run_az_cli_command("az account list --output json")

    if not subscriptions:
        print("[WARNING] No subscriptions found or user not logged in.")
        # Optionally exit or write an empty file:
        # sys.exit(1)

    # Remove 'user' field from each subscription dict
    for sub in subscriptions:
        if "user" in sub:
            del sub["user"]

    # Write results to JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(subscriptions, f, indent=2)

    print(f"[INFO] Subscriptions have been written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
