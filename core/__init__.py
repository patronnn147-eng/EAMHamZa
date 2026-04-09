import os, sys
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
# Re-export everything from app.backend.core
from app.backend.core import *
