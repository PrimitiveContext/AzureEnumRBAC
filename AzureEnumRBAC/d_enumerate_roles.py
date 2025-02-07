#!/usr/bin/env python3
"""
d_enumerate_roles.py

Enumerates all Azure role definitions (built-in and custom) and stores them in
output/d_role_definitions.json.

Usage:
  python d_enumerate_roles.py
"""

import os
import sys
import json
from tqdm import tqdm

from helpers import run_az_cli_command

OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "d_role_definitions.json")

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def main():
    # Print only before the progress bar
    print("[INFO] Enumerating all role definitions (this may take a while)...")

    ensure_output_dir_exists()

    # Run az CLI to list role definitions
    cmd = "az role definition list -o json"

    try:
        role_definitions = run_az_cli_command(cmd)
    except Exception as e:
        print(f"[ERROR] Failed to enumerate roles: {e}")
        sys.exit(1)

    # Create a single TQDM progress bar once we have the total count
    with tqdm(total=len(role_definitions), desc="Processing role definitions", unit="def") as pbar:
        # We don't need to modify the data, just iterate to update progress
        for _ in role_definitions:
            pbar.update(1)

    # After the progress bar is finished, write the entire JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(role_definitions, f, indent=2)

    # Print only after the progress bar completes
    print(f"[INFO] Successfully wrote {len(role_definitions)} role definitions to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
