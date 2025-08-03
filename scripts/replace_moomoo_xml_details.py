#!/usr/bin/env python3
"""
Moomoo OpenD Configuration Setup Script

This script automates the setup of Moomoo OpenD configuration files by:
1. Searching for Moomoo OpenD directories in the current directory tree
2. Locating OpenD.xml config files (or .sample files to rename)
3. Replacing placeholder credentials with values from environment variables

Required Environment Variables:
- MOOMOO_ACCOUNT_ID: Your Moomoo account ID
- MOOMOO_PASSWORD: Your Moomoo account password
- OPEND_PORT: (Optional) Custom port for OpenD API (defaults to existing value)

The script will only replace values that match the known Moomoo placeholders:
- Account ID: 100000
- Password: 123456
- Port: 11111

Usage:
    python setup_moomoo_config.py

Author: Zhu Weiji
"""

import logging
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format="%(name)s-%(levelname)s|%(lineno)d:  %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


# Configuration constants
class MoomooDefaults:
    """Default placeholder values that Moomoo sets in XML config files."""

    ACCOUNT_ID = "100000"
    PASSWORD = "123456"
    PORT = "11111"
    CONFIG_FILENAME = "OpenD.xml"
    SAMPLE_CONFIG_FILENAME = f"{CONFIG_FILENAME}.sample"


# Environment variable names
class EnvVars:
    """Environment variable names for configuration."""

    ACCOUNT_ID = "MOOMOO_ACCOUNT_ID"
    PASSWORD = "MOOMOO_PASSWORD"
    PORT = "OPEND_PORT"


def validate_environment_variables() -> tuple[bool, list[str]]:
    """
    Validate that required environment variables are set.

    Returns:
        Tuple of (is_valid, missing_vars_list)
    """
    required_vars = [EnvVars.ACCOUNT_ID, EnvVars.PASSWORD]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    return len(missing_vars) == 0, missing_vars


def replace_xml_field_value(
    xml_tree,
    field_name: str,
    new_value: str,
    replace_if_this_value: str | None,
):
    """
    Replace an XML field value if it matches the expected current value.

    Args:
        xml_tree: The XML ElementTree to modify
        field_name: Name of the XML field to replace
        new_value: New value to set
        expected_current_value: Only replace if current value matches this

    Returns:
        True if the field was replaced, False otherwise

    """

    root = xml_tree.getroot()
    field = root.find(field_name)

    if field is None:
        return False

    is_change = False

    if field.text == replace_if_this_value:
        if field is not None:
            field.text = new_value
            is_change = True
            log.info(f"replaced field {field_name}")

    return is_change


def find_and_prepare_moomoo_configs():
    """
    Find and prepare Moomoo OpenD configuration files.

    Searches for directories matching 'moomoo_OpenD*' pattern and:
    1. Looks for existing OpenD.xml files
    2. If not found, looks for OpenD.xml.sample files and renames them

    Returns:
        List of paths to OpenD.xml configuration files
    """
    log.info("Searching for Moomoo OpenD directories...")

    moomoo_folders = list(Path.cwd().glob("**/moomoo_OpenD*"))
    moomoo_xml_files = []

    for folder in moomoo_folders:
        if folder.is_dir():
            config_file = folder / MoomooDefaults.CONFIG_FILENAME

            if config_file.exists():
                moomoo_xml_files.append(config_file)
            else:
                # Look for the sample file
                sample_file = folder / MoomooDefaults.SAMPLE_CONFIG_FILENAME

                if sample_file.exists():
                    # Rename the sample file to remove .sample extension
                    new_file = folder / MoomooDefaults.CONFIG_FILENAME
                    new_file.write_text(sample_file.read_text(encoding="utf-8"), encoding="utf-8")

                    moomoo_xml_files.append(new_file)
                    log.info(f"Renamed {sample_file} to {new_file}")

    return moomoo_xml_files


def update_config_file(config_file: Path, credentials: dict) -> bool:
    """
    Update a single Moomoo config file with new credentials.

    Args:
        config_file: Path to the OpenD.xml file
        credentials: Dictionary containing account_id, password, and optional port

    Returns:
        True if file was successfully updated, False otherwise
    """
    log.info(f"Processing config file: {config_file}")

    try:
        # Parse the XML file
        tree = ET.parse(str(config_file))
    except ET.ParseError as e:
        log.error(f"Failed to parse XML file {config_file}: {e}")
        return False
    except FileNotFoundError:
        log.error(f"Config file not found: {config_file}")
        return False

    changes_made = False

    # Update account ID if provided
    if credentials.get("account_id"):
        if replace_xml_field_value(tree, "login_account", credentials["account_id"], MoomooDefaults.ACCOUNT_ID):
            changes_made = True

    # Update password if provided
    if credentials.get("password"):
        if replace_xml_field_value(tree, "login_pwd", credentials["password"], MoomooDefaults.PASSWORD):
            changes_made = True

    # Update port if provided
    if credentials.get("port"):
        if replace_xml_field_value(tree, "api_port", credentials["port"], MoomooDefaults.PORT):
            changes_made = True

    # Write changes back to file
    if changes_made:
        try:
            tree.write(str(config_file), encoding="utf-8", xml_declaration=True)
            log.info(f"Successfully updated config file: {config_file}")
            return True
        except OSError as e:
            log.error(f"Failed to write to config file {config_file}: {e}")
            return False
    else:
        log.info(f"No changes needed for config file: {config_file}")
        return True


def main() -> int:
    """
    Main function to orchestrate the Moomoo config setup process.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    log.info("Starting Moomoo OpenD configuration setup")

    # Validate environment variables
    env_valid, missing_vars = validate_environment_variables()
    if not env_valid:
        log.error("Missing required environment variables:")
        for var in missing_vars:
            log.error(f"  - {var}")
        log.error("Please set these environment variables and try again.")
        return 1

    # Gather credentials from environment
    credentials = {
        "account_id": os.getenv(EnvVars.ACCOUNT_ID),
        "password": os.getenv(EnvVars.PASSWORD),
        "port": os.getenv(EnvVars.PORT),  # Optional
    }

    log.info("Environment variables loaded successfully")
    if credentials["port"]:
        log.info(f"Custom port specified: {credentials['port']}")

    # Find config files
    config_files = find_and_prepare_moomoo_configs()

    if not config_files:
        log.warning("No Moomoo OpenD configuration files found")
        log.info("Make sure you have Moomoo OpenD directories in the current path")
        return 1

    log.info(f"Found {len(config_files)} configuration file(s) to process")

    # Process each config file
    success_count = 0
    for config_file in config_files:
        if update_config_file(config_file, credentials):
            success_count += 1

    # Report results
    if success_count == len(config_files):
        log.info(f"Successfully processed all {success_count} configuration file(s)")
        return 0
    else:
        log.error(f"Only {success_count}/{len(config_files)} files processed successfully")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(1)
