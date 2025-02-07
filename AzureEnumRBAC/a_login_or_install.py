#!/usr/bin/env python3

"""
a_login_or_install.py

This script checks if the Azure CLI (az) is installed.
If it isn't:
  - On Windows, offers to install via MSI (32-bit or 64-bit)
    using the snippet you provided (known to work).
  - On Linux (Debian/Ubuntu), offers to run Microsoft's official
    install script via curl.
  - On macOS, offers to install via Homebrew.

After installation, attempts 'az login' to authenticate the user.

References:
  - Windows: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows
  - Linux (Debian/Ubuntu): https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux
  - macOS: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos
"""

import subprocess
import sys
import platform

##########################################
#  Windows-Specific: REPLACED WITH YOURS #
##########################################

def is_az_installed_windows():
    """
    Checks if the 'az' CLI is installed (Windows) by attempting
    to run 'az --version' with shell=True.
    Returns True if installed, False otherwise.
    """
    try:
        subprocess.run(
            ["az", "--version"],
            check=True,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_azure_cli_windows(architecture="32"):
    """
    Installs the Azure CLI on Windows using PowerShell + MSI,
    known-working snippet.
    :param architecture: '32' or '64', defaults to '32'
    """
    if architecture == "64":
        download_url = "https://aka.ms/installazurecliwindowsx64"
    else:
        download_url = "https://aka.ms/installazurecliwindows"

    ps_command = (
        f"$ProgressPreference = 'SilentlyContinue'; "
        f"Invoke-WebRequest -Uri {download_url} -OutFile .\\AzureCLI.msi; "
        f"Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'; "
        f"Remove-Item .\\AzureCLI.msi"
    )

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command", ps_command
            ],
            check=True
        )
        print("Azure CLI installation completed.")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to install Azure CLI.")
        print("Details:", e)
        sys.exit(1)


def login_to_azure_windows():
    """
    Attempts to log in to Azure CLI (az login) with shell=True (Windows).
    """
    try:
        print("Login process initiated (wait for popup).")
        subprocess.run(
            ["az", "login"],
            check=True,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("Successfully logged in to Azure CLI.")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to login with Azure CLI.")
        print("Details:", e)
        sys.exit(1)

##################################################
#   Linux/Mac Cross-Platform Portions (original) #
##################################################

def is_az_installed():
    """
    Checks if the 'az' CLI is installed on non-Windows systems (or general check).
    Returns True if installed, False otherwise.
    """
    try:
        subprocess.run(
            ["az", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_azure_cli_linux_deb():
    """
    Installs the Azure CLI on Linux (Debian/Ubuntu) by curling
    the official Microsoft install script.
    """
    print("Using the Debian/Ubuntu install script from Microsoft.")
    cmd = """curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"""
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("Azure CLI installation completed (Linux Debian/Ubuntu).")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to install Azure CLI on Linux.")
        print("Details:", e)
        sys.exit(1)

def install_azure_cli_macos():
    """
    Installs the Azure CLI on macOS via Homebrew.
    Requires Homebrew to be installed.
    """
    try:
        subprocess.run(["brew", "--version"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("[ERROR] Homebrew is not installed on this macOS system.")
        print("Install Homebrew first: https://brew.sh/")
        sys.exit(1)

    try:
        subprocess.run(["brew", "update"], check=True)
        subprocess.run(["brew", "install", "azure-cli"], check=True)
        print("Azure CLI installation completed (macOS).")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to install Azure CLI on macOS.")
        print("Details:", e)
        sys.exit(1)

def login_to_azure():
    """
    Generic login for non-Windows (or if you prefer the original method).
    """
    try:
        print("Login process initiated (wait for browser or device code prompts).")
        subprocess.run(
            ["az", "login"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("Successfully logged in to Azure CLI.")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to login with Azure CLI.")
        print("Details:", e)
        sys.exit(1)

###########
#  main()  #
###########

def main():
    current_os = platform.system().lower()

    if current_os == "windows":
        # Use the known-working Windows snippet
        if is_az_installed_windows():
            print("Azure CLI is already installed on this Windows system.")
            login_choice = input("Would you like to log in now? [y/n]: ").strip().lower()
            if login_choice == "y":
                login_to_azure_windows()
            else:
                print("Login skipped.")
        else:
            print("Azure CLI is not installed on this Windows system.")
            choice = input("Would you like to install Azure CLI now? [y/n]: ").strip().lower()
            if choice == "y":
                arch_choice = input("Which version would you like to install? [32/64]: ").strip()
                if arch_choice not in ["32", "64"]:
                    print("[ERROR] Invalid choice. Please run the script again and select '32' or '64'.")
                    sys.exit(1)

                print(f"Installing {arch_choice}-bit Azure CLI... (may take up to 5 min)")
                install_azure_cli_windows(arch_choice)

                # After installation, attempt to login
                if is_az_installed_windows():
                    login_to_azure_windows()
                else:
                    print("[ERROR] Azure CLI did not install correctly. Exiting.")
                    sys.exit(1)
            else:
                print("Installation aborted by user.")

    elif current_os == "linux":
        # Linux path
        if is_az_installed():
            print("Azure CLI is already installed on this Linux system.")
            login_choice = input("Would you like to log in now? [y/n]: ").strip().lower()
            if login_choice == "y":
                login_to_azure()
            else:
                print("Login skipped.")
        else:
            print("Azure CLI is not installed on this Linux system.")
            choice = input("Would you like to install Azure CLI (Debian/Ubuntu) now? [y/n]: ").strip().lower()
            if choice == "y":
                install_azure_cli_linux_deb()
                if is_az_installed():
                    login_to_azure()
                else:
                    print("[ERROR] Azure CLI did not install correctly. Exiting.")
                    sys.exit(1)
            else:
                print("Installation aborted by user.")

    elif current_os == "darwin":
        # macOS path
        if is_az_installed():
            print("Azure CLI is already installed on this macOS system.")
            login_choice = input("Would you like to log in now? [y/n]: ").strip().lower()
            if login_choice == "y":
                login_to_azure()
            else:
                print("Login skipped.")
        else:
            print("Azure CLI is not installed on this macOS system.")
            choice = input("Would you like to install Azure CLI (Homebrew) now? [y/n]: ").strip().lower()
            if choice == "y":
                install_azure_cli_macos()
                if is_az_installed():
                    login_to_azure()
                else:
                    print("[ERROR] Azure CLI did not install correctly. Exiting.")
                    sys.exit(1)
            else:
                print("Installation aborted by user.")

    else:
        # Unsupported OS
        print(f"[ERROR] Unrecognized or unsupported OS: {platform.system()}")
        print("Please install Azure CLI manually: https://learn.microsoft.com/cli/azure")
        sys.exit(1)

if __name__ == "__main__":
    main()
