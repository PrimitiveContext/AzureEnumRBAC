#!/usr/bin/env python3

"""
azure_cli_crossplatform.py

Checks if the Azure CLI is installed (by running 'az --version').
If it isn't:
  - On Windows, offers to install via MSI (32-bit or 64-bit).
  - On Linux (Debian/Ubuntu), offers to run Microsoft's official install script via curl.
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

def is_az_installed():
    """
    Checks if the 'az' CLI is installed by attempting to run 'az --version'.
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

def login_to_azure():
    """
    Attempts to log in to Azure CLI (az login).
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

##################################
#  Windows Installation Helpers  #
##################################

def install_azure_cli_windows(architecture="32"):
    """
    Installs the Azure CLI on Windows using PowerShell + MSI.
    :param architecture: '32' or '64', defaults to '32'
    """
    if architecture == "64":
        download_url = "https://aka.ms/installazurecliwindowsx64"
    else:
        download_url = "https://aka.ms/installazurecliwindows"

    # PowerShell command to download the MSI and install it silently
    ps_command = (
        f"$ProgressPreference = 'SilentlyContinue'; "
        f"Invoke-WebRequest -Uri {download_url} -OutFile .\\AzureCLI.msi; "
        f"Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'; "
        f"Remove-Item .\\AzureCLI.msi"
    )

    try:
        # Run PowerShell
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command", ps_command
            ],
            check=True
        )
        print("Azure CLI installation completed (Windows).")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to install Azure CLI on Windows.")
        print("Details:", e)
        sys.exit(1)

##############################
#  Linux Installation Helper #
##############################

def install_azure_cli_linux_deb():
    """
    Installs the Azure CLI on Linux (Debian/Ubuntu) by curling
    the official Microsoft install script.
    """
    # This approach won't work on all distros. Adjust for your environment.
    # See https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux
    print("Using the Debian/Ubuntu install script from Microsoft.")
    cmd = """curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"""
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("Azure CLI installation completed (Linux Debian/Ubuntu).")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to install Azure CLI on Linux.")
        print("Details:", e)
        sys.exit(1)

##############################
#  macOS Installation Helper #
##############################

def install_azure_cli_macos():
    """
    Installs the Azure CLI on macOS via Homebrew.
    Requires Homebrew to be installed.
    """
    try:
        subprocess.run(["brew", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

###########
#  main()  #
###########

def main():
    current_os = platform.system().lower()

    if is_az_installed():
        print("Azure CLI is already installed on this system.")
        login_choice = input("Would you like to log in now? [y/n]: ").strip().lower()
        if login_choice == "y":
            login_to_azure()
        else:
            print("Login skipped.")
        return

    # Azure CLI not installed => Offer to install
    print("Azure CLI is not installed on this system.")
    choice = input("Would you like to install Azure CLI now? [y/n]: ").strip().lower()
    if choice != "y":
        print("Installation aborted by user.")
        sys.exit(0)

    # OS-specific installation
    if current_os == "windows":
        arch_choice = input("Which version would you like to install? [32/64]: ").strip()
        if arch_choice not in ["32", "64"]:
            print("[ERROR] Invalid choice. Please run again and select '32' or '64'.")
            sys.exit(1)

        print(f"Installing {arch_choice}-bit Azure CLI on Windows... (may take a few minutes)")
        install_azure_cli_windows(arch_choice)

    elif current_os == "linux":
        # Attempt Debian/Ubuntu script
        print("Installing Azure CLI on Linux (Debian/Ubuntu-based).")
        install_azure_cli_linux_deb()

    elif current_os == "darwin":
        # macOS
        print("Installing Azure CLI on macOS via Homebrew...")
        install_azure_cli_macos()

    else:
        print(f"[ERROR] Unrecognized or unsupported OS: {platform.system()}")
        print("Please install Azure CLI manually: https://learn.microsoft.com/cli/azure")
        sys.exit(1)

    # After installation, verify & login if successful
    if is_az_installed():
        print("Azure CLI installed successfully.")
        login_to_azure()
    else:
        print("[ERROR] Azure CLI did not install correctly. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
