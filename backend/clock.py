"""Clinical dates follow the unit timezone; audit timestamps remain UTC."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo


def today():
    return datetime.now(ZoneInfo(os.environ.get("APP_TIMEZONE", "America/Cuiaba"))).date()
