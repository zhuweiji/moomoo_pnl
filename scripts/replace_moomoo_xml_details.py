"""Searches the current directory for Moomoo's config file format, and replaces the placeholder username and passwords with the user's credentials stored in environment variables."""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    format="%(name)s-%(levelname)s|%(lineno)d:  %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# the default values that moomoo sets in the xml file
PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_ID = "100000"
PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_PASSWORD = "123456"

MOOMOO_CONFIG_FILENAME = "OpenD.xml"

if __name__ == "__main__":
    moomoo_xml_files = list(Path.cwd().glob(f"**/{MOOMOO_CONFIG_FILENAME}"))

    account_id = os.getenv("MOOMOO_ACCOUNT_ID")
    account_password = os.getenv("MOOMOO_PASSWORD")

    log.info(f"Found {len(moomoo_xml_files)} Moomoo config files")

    for file in moomoo_xml_files:
        tree = ET.parse(str(file))
        root = tree.getroot()

        login_account = root.find("login_account")
        login_pwd = root.find("login_pwd")

        is_changed = False

        if login_account is not None:
            log.info(login_account.text == PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_ID)

            if login_account.text == PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_ID:
                message = f"Found default value for login_account in file {file}"
                if account_id:
                    login_account.text = account_id
                    message += f", replacing with {account_id}"
                log.info(message)
                is_changed = True

        if login_pwd is not None:
            if login_pwd.text == PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_PASSWORD:
                message = f"Found default value for login_pwd in file {file}"
                if account_password:
                    login_pwd.text = account_password
                    message += f", replacing with {account_password}"
                log.info(message)
                is_changed = True

        if is_changed:
            tree.write(str(file))
            log.info(f"Updated file {file}")
