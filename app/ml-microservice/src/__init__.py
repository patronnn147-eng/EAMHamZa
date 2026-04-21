# ML Microservice Source Package
#
# numpy._core compatibility shim
# --------------------------------
# Models pickled with numpy >=2.0 reference the internal path `numpy._core.*`.
# We run under numpy 1.26.x (to stay within lifelines' numpy<2.0 constraint).
# In numpy 1.x the same content lives at `numpy.core`; we register it under
# the 2.x name so that pickle / joblib can deserialise those .pkl files.
import sys
import types

try:
    import numpy as _np
    if not hasattr(_np, '_core'):
        import numpy.core as _np_core
        # Register the package alias
        sys.modules.setdefault('numpy._core', _np_core)
        # Register every public sub-module that numpy.core exposes
        for _attr in dir(_np_core):
            _mod = getattr(_np_core, _attr, None)
            if isinstance(_mod, types.ModuleType):
                sys.modules.setdefault(f'numpy._core.{_attr}', _mod)
        del _np_core
    del _np
except Exception:
    pass  # best-effort — don't break startup if shim fails
