#!/usr/bin/env python3
"""
AzureEnumRBAC.py

Orchestrator that runs enumeration sub-scripts in the user's current directory,
redirecting "output" references to <pwd>/AzureEnumRBAC/output.

Usage:
  AzureEnumRBAC
    (installed as a console_script entry point in pyproject.toml)
"""

import os
import sys
import subprocess
import json
import shutil
import re

# The sub-scripts to run, in order:
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
    "l_bubble_chart_users.py",
    "m_bubble_chart_roles.py"
]

# Find where these sub-scripts actually live (the installed package directory).
THIS_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

# The user’s current working directory:
USER_CWD = os.getcwd()

# We want sub-scripts to place outputs in: <pwd>/AzureEnumRBAC/output
USER_BASE_PATH = os.path.join(USER_CWD, "AzureEnumRBAC")
USER_OUTPUT_DIR = os.path.join(USER_BASE_PATH, "output")
USER_FINAL_DIR  = os.path.join(USER_BASE_PATH, "FINAL_OUTPUT")

# We'll keep a small JSON log in <pwd>/AzureEnumRBAC/output/AzureEnumRBAC_run.log
RUN_LOG_FILE = os.path.join(USER_OUTPUT_DIR, "AzureEnumRBAC_run.log")


def load_run_log():
    """Load run log if present; return last_completed index or -1 if missing."""
    if os.path.exists(RUN_LOG_FILE):
        try:
            with open(RUN_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_completed", -1)
        except Exception:
            return -1
    return -1


def save_run_log(index):
    """Write run log with {'last_completed': index}."""
    data = {"last_completed": index}
    with open(RUN_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def run_phase_script(script_name, index):
    """
    Run a single sub-script from THIS_PACKAGE_DIR, but cwd=<pwd>/AzureEnumRBAC.

    So if sub-script does 'os.makedirs("output", exist_ok=True)', it lands in
    <pwd>/AzureEnumRBAC/output instead of the library install folder.
    """
    script_path = os.path.join(THIS_PACKAGE_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found in package: {script_path}")
        sys.exit(1)

    print(f"[INFO] Running phase {index}: {script_name}")
    cmd = [sys.executable, script_path]
    try:
        subprocess.run(cmd, check=True, cwd=USER_BASE_PATH)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Phase script failed: {script_name}")
        sys.exit(e.returncode)


def copy_final_outputs():
    """
    Copy files from <pwd>/AzureEnumRBAC/output that start with i_, j_, k_, l_, or m_
    into <pwd>/AzureEnumRBAC/FINAL_OUTPUT, removing the prefix from each filename.
    """
    if not os.path.exists(USER_FINAL_DIR):
        os.makedirs(USER_FINAL_DIR, exist_ok=True)

    pattern = re.compile(r'^[ijklm]_')
    final_filenames = []

    for file_name in os.listdir(USER_OUTPUT_DIR):
        if pattern.match(file_name):
            old_path = os.path.join(USER_OUTPUT_DIR, file_name)
            # remove first two chars: 'i_', 'j_', etc.
            new_file_name = file_name[2:]
            new_path = os.path.join(USER_FINAL_DIR, new_file_name)

            if os.path.isfile(old_path):
                shutil.copy2(old_path, new_path)
                final_filenames.append(new_file_name)

    if final_filenames:
        print("\n=========================================================")
        print(" Final Output Files Created in AzureEnumRBAC/FINAL_OUTPUT:")
        print("=========================================================")
        for fname in final_filenames:
            print(f"  {fname}")
        print("=========================================================\n")
    else:
        print("\nNo matching final output files (i_, j_, k_, l_, m_) were found.\n")


def main():
    # 1) Ensure <pwd>/AzureEnumRBAC/output exists (for logs + sub-script data)
    if not os.path.exists(USER_OUTPUT_DIR):
        os.makedirs(USER_OUTPUT_DIR, exist_ok=True)

    total_scripts = len(SCRIPTS_IN_ORDER)
    last_completed = load_run_log()

    if last_completed < 0:
        # Fresh run
        start_index = 0
        print("[INFO] No existing run log found in current directory. Starting at phase #0 ...")
    else:
        resume_index = last_completed + 1
        if resume_index >= total_scripts:
            print("[INFO] The run log indicates all scripts have completed already.")
            choice = input("Re-run everything from the beginning? [y/n]: ").strip().lower()
            if choice == "y":
                start_index = 0
                save_run_log(-1)
            else:
                print("Okay, exiting.")
                sys.exit(0)
        else:
            script_next = SCRIPTS_IN_ORDER[resume_index]
            print(f"[INFO] Found existing run log: last completed index = {last_completed}.")
            print(f"[INFO] Next script is {resume_index}: {script_next}")
            choice = input("Resume (r) or start over (s)? [r/s]: ").strip().lower()
            if choice == "s":
                start_index = 0
                save_run_log(-1)
            else:
                start_index = resume_index

    # 2) Main loop
    for i in range(start_index, total_scripts):
        script_name = SCRIPTS_IN_ORDER[i]
        run_phase_script(script_name, i)
        save_run_log(i)

    print("\n[INFO] All phases completed successfully.\n")
    copy_final_outputs()


if __name__ == "__main__":
    main()
