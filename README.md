# AzureEnumRBAC

**AzureEnumRBAC** is a Python CLI tool that enumerates Azure resources,
subscriptions, resource groups, role definitions, and role assignments.
It also aggregates nested group membership information and produces
various CSV/JSON/HTML outputs (like bubble charts for users/roles).

## Table of Contents

1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
   1. [Install from GitHub](#install-from-github)
   2. [Local Installation](#local-installation)
4. [Usage](#usage)
5. [Repository Structure](#repository-structure)
6. [Contributing](#contributing)
7. [License](#license)

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

Once installed, add the script directory to PATH and run:

    AzureEnumRBAC

OR, if you want a quick one-liner to find and run the binary for your operating system, try one of the following:
 
    <Windows> where AzureEnumRBAC && AzureEnumRBAC
    <Linux> which AzureEnumRBAC && AzureEnumRBAC
    <macOS> which AzureEnumRBAC && AzureEnumRBAC

You should see the CLI script orchestrating each enumeration phase.
It will create an `output/` folder under `AzureEnumRBAC/AzureEnumRBAC/`
or wherever your code references the output path.

You can modify or re-run phases independently (a_login_or_install, b_get_subscriptions,
etc.), or rely on the main CLI to chain them.

**Example**:

1. Log in with `az login` if the CLI isn't installed automatically.
2. Enumerate subscriptions, role assignments, group memberships.
3. View aggregated data in `output/*.json` or `output/*.csv`.
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

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more details.
