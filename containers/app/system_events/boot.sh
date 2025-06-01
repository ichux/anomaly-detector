#!/bin/sh

set -e

python3 <<END
import os
from itsup import wait_for_route

wait_for_route(f"http://{os.getenv("APP_INTERNAL_HOST")}:80/status")

END

python3 -m system_events.runner
