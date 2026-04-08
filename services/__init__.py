import os, sys
# Add the actual backend services directory to the import path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'backend', 'services'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

