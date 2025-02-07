# AzureEnumRBAC

AzureEnumRBAC is a Python CLI tool that enumerates Azure resources,
subscriptions, resource groups, role definitions, and role assignments.
It also aggregates nested group membership information and produces
various CSV/JSON/HTML outputs (like bubble charts for users/roles).

## Table of Contents

1. Features
2. Prerequisites
3. Installation
   1. Install from GitHub
   2. Local Installation
4. Usage
5. Repository Structure
6. Contributing
7. License

## Features

- Automatic login or installation of Azure CLI on Windows
- Enumerates:
  - Subscriptions
  - Resource groups
  - Azure role definitions
  - Role assignments
- Aggregates user or group membership data
- Creates final CSV or JSON output plus bubble chart HTML
- Allows partial or full re-runs with a simple orchestrator script

## Prerequisites

- Python 3.7+ (earlier versions may work, but are untested)
- Azure CLI installed (the tool can install it if not found on Windows)
- Permissions to read Azure subscriptions, role assignments, etc.

## Installation

### Install from GitHub

If you have a GitHub repository like:

    pip install git+https://github.com/PrimitiveContext/AzureEnumRBAC.git

### Local Installation

Clone or download this repository, then run:

    cd AzureEnumRBAC
    pip install .

## Usage

After installation, a console command "AzureEnumRBAC" is placed in your environment’s
Scripts (Windows) or bin (Linux/macOS) folder. Make sure that folder is on your PATH.

If you want a quick one-liner to find and run the binary for your operating system,
try one of the following:

- Windows (Command Prompt):

    where AzureEnumRBAC && AzureEnumRBAC

- Linux:

    which AzureEnumRBAC && AzureEnumRBAC

- macOS:

    which AzureEnumRBAC && AzureEnumRBAC

Alternatively, you can simply run:

    AzureEnumRBAC

if the script folder is already on your PATH.

Upon running the command, you should see the CLI script orchestrating each enumeration phase.
It will create an output/ folder under AzureEnumRBAC/AzureEnumRBAC/
(or wherever your code references the output path).

You can modify or re-run phases independently (e.g., a_login_or_install, b_get_subscriptions,
etc.), or rely on the main CLI to chain them.

Example workflow:
1. Log in with az login if the CLI isn't installed automatically.
2. Enumerate subscriptions, role assignments, group memberships.
3. View aggregated data in output/*.json or output/*.csv.
4. Generate user or role bubble charts and open them in your browser.

## Repository Structure

AzureEnumRBAC/
├── AzureEnumRBAC/
│   ├── __init__.py
│   ├── azureEnum.py  (main orchestration)
│   ├── a_login_or_install.py
│   ├── b_get_subscriptions.py
│   ├── c_enumerate_resources.py
│   ├── ...
├── pyproject.toml
├── README.md
└── LICENSE

## Contributing

- Fork this repository.
- Create a feature branch for your changes.
- Submit a pull request describing your enhancement.

## License

Distributed under the MIT License. See LICENSE for more details.
