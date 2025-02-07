import subprocess
import json
import sys

def run_az_cli_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {command}")
        print(f"[ERROR] CLI error: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON output from command: {command}")
        print(f"[ERROR] Output was: {result.stdout}")
        sys.exit(1)

def get_msgraph_token():
    cmd = "az account get-access-token --resource-type ms-graph -o json"
    data = run_az_cli_command(cmd)
    return data["accessToken"]