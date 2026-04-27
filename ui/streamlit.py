import importlib.util
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(ROOT, "ui", "app.py")

spec = importlib.util.spec_from_file_location("careplus_app", APP_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)

main = module.main


if __name__ == "__main__":
    main()
