import os

from .project_secrets import *

# this stuff is stored in envvars until there's enough of them that making a top-level config.yml makes sense
SITE_PORT = int(os.environ["OPEND_PORT"])
NTFY_SH_TOPIC = os.environ["NTFY_SH_TOPIC"]
