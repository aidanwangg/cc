from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance. Lives in its own module so both main.py (which
# registers it on the app) and the routers (which decorate endpoints) can
# import it without a circular dependency.
limiter = Limiter(key_func=get_remote_address)
