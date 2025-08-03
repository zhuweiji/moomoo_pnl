"""Searches the current directory for Moomoo's config file format, and replaces the placeholder username and passwords with the user's credentials stored in environment variables."""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(format="%(name)s-%(levelname)s|%(lineno)d:  %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# the default values that moomoo sets in the xml file
PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_ID = "100000"
PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_PASSWORD = "123456"
PLACEHOLDER_MOOMOO_PORT = "11111"

MOOMOO_CONFIG_FILENAME = "OpenD.xml"


def replace_xml_value(
    xml_tree,
    field_name: str,
    new_value: str,
    replace_if_this_value: str | None,
):
    root = xml_tree.getroot()
    field = root.find(field_name)

    if field is None:
        return xml_tree

    if field.text == replace_if_this_value:
        if field is not None:
            field.text = new_value
            log.info(f"replaced field {field_name}")

    return xml_tree


if __name__ == "__main__":
    moomoo_xml_files = list(Path.cwd().glob(f"**/{MOOMOO_CONFIG_FILENAME}"))

    account_id = os.getenv("MOOMOO_ACCOUNT_ID")
    account_password = os.getenv("MOOMOO_PASSWORD")
    opend_port = os.getenv("OPEND_PORT")

    log.info(f"Found {len(moomoo_xml_files)} Moomoo config files")

    for file in moomoo_xml_files:
        tree = ET.parse(str(file))

        is_changed = False

        if account_id:
            tree = replace_xml_value(
                xml_tree=tree,
                field_name="login_account",
                new_value=account_id,
                replace_if_this_value=PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_ID,
            )

        if account_password:
            tree = replace_xml_value(
                xml_tree=tree,
                field_name="login_pwd",
                new_value=account_password,
                replace_if_this_value=PLACEHOLDER_MOOMOO_LOGIN_ACCOUNT_PASSWORD,
            )

        if opend_port:
            tree = replace_xml_value(
                xml_tree=tree,
                field_name="api_port",
                new_value=opend_port,
                replace_if_this_value=PLACEHOLDER_MOOMOO_PORT,
            )

        tree.write(str(file))
        log.info(f"Updated file {file}")
