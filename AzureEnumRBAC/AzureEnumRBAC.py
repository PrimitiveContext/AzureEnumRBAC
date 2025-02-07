#!/usr/bin/env python3
"""
AzureEnumRBAC.py

An orchestrator for the Azure enumeration scripts, with resume/restart logic
and a single output folder at AzureEnumRBAC/output. Sub-scripts run in the
AzureEnumRBAC/ directory so that all references to "output" in the scripts 
actually point to AzureEnumRBAC/output (no duplicates).

Directory structure:
  your_project/
    AzureEnumRBAC.py  <-- this file
    AzureEnumRBAC/
      a_login_or_install.py
      b_get_subscriptions.py
      c_enumerate_resources.py
      d_enumerate_roles.py
      e_enumerate_assignments.py
      f_enumerate_group_members.py
      g_combine_rbac_users.py
      h_get_user_personal_data.py
      i_combine_identities.py
      j_role_matrix.py
      k_user_matrix.py
      l_bubble_chart_roles.py
      m_bubble_chart_users.py
      helpers.py
      output/

Usage:
  python AzureEnumRBAC.py
    - Runs all phases in order (a through m).
    - If interrupted, you can run it again; it will detect the run log 
      at 'AzureEnumRBAC/output/AzureEnumRBAC_run.log' and let you resume.

If a script fails (nonzero exit), the entire process stops. 
"""

import os
import sys
import subprocess
import json
import shutil
import re

# The scripts to run, in order:
SCRIPTS_IN_ORDER = [
    "a_login_or_install.py",
    "b_get_subscriptions.py",
    "c_enumerate_resources.py",
    "d_enumerate_roles.py",
    "e_enumerate_assignments.py",
    "f_enumerate_group_members.py",
    "g_combine_rbac_users.py",
    "h_get_user_personal_data.py",
    "i_combine_identities.py",
    "j_role_matrix.py",
    "k_user_matrix.py",
    "l_bubble_chart_roles.py",
    "m_bubble_chart_users.py"
]

# We'll store a tiny JSON like {"last_completed": 3} to indicate which script index was last successful
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = BASE_DIR       # We'll run sub-scripts in this directory
OUTPUT_DIR = os.path.join(os.getcwd(), "AzureEnumRBAC")        # So all references to "output" from sub-scripts => AzureEnumRBAC/output
RUN_LOG_FILE = os.path.join(OUTPUT_DIR, "AzureEnumRBAC_run.log")

# Final output directory (in the same folder as AzureEnumRBAC.py):
FINAL_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "FINAL_OUTPUT")


def load_run_log():
    """
    Loads run log if present, returns integer last_completed.
    If missing or error, return -1.
    """
    if os.path.exists(RUN_LOG_FILE):
        try:
            with open(RUN_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_completed", -1)
        except Exception:
            return -1
    return -1


def save_run_log(index):
    """
    Write run log with {"last_completed": index} to AzureEnumRBAC_run.log.
    """
    data = {"last_completed": index}
    with open(RUN_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def run_phase_script(script_name, index):
    """
    Runs a single script by name, from within AzureEnumRBAC/ as cwd.
    If script fails, we exit entirely.
    """
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found: {script_path}")
        sys.exit(1)

    print(f"[INFO] Running phase {index} script: {script_name}")
    cmd = [sys.executable, script_path]
    try:
        # The key: run in SCRIPT_DIR so all references to "output" => AzureEnumRBAC/output
        subprocess.run(cmd, check=True, cwd=SCRIPT_DIR)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Phase script failed: {script_name}")
        sys.exit(e.returncode)


def copy_final_outputs():
    """
    After all scripts complete, copy files from AzureEnumRBAC/output whose names
    start with i_, j_, k_, l_, or m_ into AzureEnumRBAC_FINAL_OUTPUT,
    removing the letter-underscore prefix from each filename.
    Print a simple ASCII summary of the final file outputs.
    """
    # Create AzureEnumRBAC_FINAL_OUTPUT if it doesn't exist
    if not os.path.exists(FINAL_OUTPUT_DIR):
        os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

    # Regex to match filenames starting with i_, j_, k_, l_, or m_
    pattern = re.compile(r'^[ijklm]_')

    final_filenames = []
    for file_name in os.listdir(OUTPUT_DIR):
        if pattern.match(file_name):
            old_path = os.path.join(OUTPUT_DIR, file_name)
            # Remove the first two chars (letter + underscore) from the filename
            new_file_name = file_name[2:]
            new_path = os.path.join(FINAL_OUTPUT_DIR, new_file_name)

            if os.path.isfile(old_path):
                shutil.copy2(old_path, new_path)
                final_filenames.append(new_file_name)

    if final_filenames:
        print("\n=========================================================")
        print(" Final Output Files Created in AzureEnumRBAC_FINAL_OUTPUT:")
        print("=========================================================")
        for fname in final_filenames:
            print(f"  {fname}")
        print("=========================================================\n")
    else:
        print("\nNo matching final output files (i_, j_, k_, l_, m_) were found.\n")


def main():
    # Make sure AzureEnumRBAC/output directory exists for logs
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_scripts = len(SCRIPTS_IN_ORDER)
    last_completed = load_run_log()

    if last_completed < 0:
        # no log => fresh
        start_index = 0
        print("[INFO] No existing run log found. Starting from script #0 ...")
    else:
        # we have a run log
        resume_index = last_completed + 1
        if resume_index >= total_scripts:
            print("[INFO] The run log indicates all scripts have completed already.")
            choice = input("Re-run everything from the beginning? [y/n]: ").strip().lower()
            if choice == "y":
                start_index = 0
                save_run_log(-1)  # reset
            else:
                print("Okay, exiting.")
                sys.exit(0)
        else:
            script_next = SCRIPTS_IN_ORDER[resume_index]
            print(f"[INFO] Found existing run log. Last completed index = {last_completed}.")
            print(f"[INFO] Next script is index {resume_index}: {script_next}")
            choice = input("Resume (r) or start over (s)? [r/s]: ").strip().lower()
            if choice == "s":
                start_index = 0
                save_run_log(-1)  # reset
            else:
                start_index = resume_index

    # Main loop
    for i in range(start_index, total_scripts):
        script_name = SCRIPTS_IN_ORDER[i]
        run_phase_script(script_name, i)
        # If successful, update run log
        save_run_log(i)

    print("\n[INFO] All phases completed successfully.")

    # Copy final output files after all scripts complete
    copy_final_outputs()


if __name__ == "__main__":
    main()
