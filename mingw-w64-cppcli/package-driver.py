# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Installed frontend defaults; explicit flags/environment still take priority."""
import os
from pathlib import Path
import runpy

here = Path(__file__).resolve().parent
prefix = here.parents[1]
os.environ.setdefault("CPPCLI_SDK", str(prefix / "lib/dotnet"))
os.environ.setdefault("CPPCLI_ILASM", str(prefix / "bin/ilasm-dotnet.exe"))
os.environ.setdefault("CPPCLI_CLANG", str(prefix / "bin/clang++.exe"))
runpy.run_path(str(here / "cli-clang.py"), run_name="__main__")
