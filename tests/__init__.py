import sys
import types


if "pyvista" not in sys.modules:
    sys.modules["pyvista"] = types.ModuleType("pyvista")
