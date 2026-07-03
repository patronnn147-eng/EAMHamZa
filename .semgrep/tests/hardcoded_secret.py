import os

# ruleid: hardcoded-secret-default
SECRET_KEY = os.getenv("SECRET_KEY", "changeme-default-secret")

# ok: hardcoded-secret-default
SECRET_KEY_SAFE = os.getenv("SECRET_KEY", "")

# ruleid: hardcoded-secret-default
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-secret")

# ok: hardcoded-secret-default
JWT_SECRET_SAFE = os.environ.get("JWT_SECRET")
