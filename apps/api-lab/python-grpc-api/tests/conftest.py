import pathlib
import sys

_src_generated = pathlib.Path(__file__).parent.parent / "src" / "generated"
if str(_src_generated) not in sys.path:
    sys.path.insert(0, str(_src_generated))
