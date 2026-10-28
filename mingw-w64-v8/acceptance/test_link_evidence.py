#!/usr/bin/env python3
"""Check linker path evidence parsing; these checks do not validate binaries."""
import importlib.util
from pathlib import Path
import shlex
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("audit_build", Path(__file__).with_name("audit_build.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class LinkEvidence(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.out = self.root / "out"
        self.library = self.root / "SDK with spaces/lib/libv8.dll.a"

    def test_library_outside_response_file(self):
        command = "g++ -o content_shell.exe @content_shell.exe.rsp " + shlex.quote(self.library.as_posix())
        self.assertTrue(audit.refers_to_import(command, self.library, self.out))

    def test_relative_response_file_path(self):
        self.assertTrue(audit.refers_to_import('"../SDK with spaces/lib/libv8.dll.a"', self.library, self.out))

    def test_forwarded_linker_argument(self):
        argument = "-Wl," + self.library.as_posix()
        self.assertTrue(audit.refers_to_import(shlex.quote(argument), self.library, self.out))

    def test_same_filename_from_another_sdk(self):
        other = self.root / "another-sdk/lib/libv8.dll.a"
        self.assertFalse(audit.refers_to_import(shlex.quote(other.as_posix()), self.library, self.out))

    def test_filename_fragment_is_not_a_library(self):
        self.assertFalse(audit.refers_to_import(shlex.quote(self.library.as_posix() + ".old"), self.library, self.out))

    @unittest.skipUnless(shutil.which("ninja"), "Ninja is not installed")
    def test_compile_evidence_excludes_unrelated_binary(self):
        self.out.mkdir()
        (self.out / "build.ninja").write_text('''rule cxx
  command = c++ -c $in -o $out
rule link
  command = c++ $in -o $out
build consumer.o: cxx consumer.cc
build unrelated.o: cxx tracing_muxer_impl.cc
build content_shell.exe: link consumer.o
build unrelated.exe: link unrelated.o
''')
        commands = audit.target_commands("ninja", self.out, "content_shell.exe")
        files = {Path(entry["file"]).name for entry in commands}
        self.assertIn("consumer.cc", files)
        self.assertNotIn("tracing_muxer_impl.cc", files)


if __name__ == "__main__":
    unittest.main()
