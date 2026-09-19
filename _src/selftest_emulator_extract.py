# -*- coding: utf-8 -*-
"""Selftest for emulator archive extraction and FAT32 compatibility.

Runs offline and headless on the build machine.
"""

import os
import sys
import shutil
import tempfile
import tarfile
import unittest

# Point to app files
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_DIR = os.path.join(REPO_ROOT, "files")
if FILES_DIR not in sys.path:
    sys.path.insert(0, FILES_DIR)

from rh.storage import unlock
from rh.emulator_store import safe_extract_tar_gz, install_emu
from rh import paths


class TestEmulatorExtract(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="rh_test_emu_")
        self.orig_emus_dir = paths.EMUS_DIR
        self.orig_roms_dir = paths.ROMS_DIR
        paths.EMUS_DIR = os.path.join(self.tmp_dir, "Emus")
        paths.ROMS_DIR = os.path.join(self.tmp_dir, "Roms")
        os.makedirs(paths.EMUS_DIR, exist_ok=True)
        os.makedirs(paths.ROMS_DIR, exist_ok=True)

    def tearDown(self):
        paths.EMUS_DIR = self.orig_emus_dir
        paths.ROMS_DIR = self.orig_roms_dir
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_test_archive(self, sys_id="TESTEMU"):
        archive_path = os.path.join(self.tmp_dir, f"{sys_id}.tar.gz")
        source_dir = os.path.join(self.tmp_dir, "src_" + sys_id)
        emu_dir = os.path.join(source_dir, sys_id)
        os.makedirs(os.path.join(emu_dir, "subdir", "bin"), exist_ok=True)

        # Write files
        with open(os.path.join(emu_dir, "launch.sh"), "w") as f:
            f.write("#!/bin/sh\necho running\n")
        with open(os.path.join(emu_dir, "config.json"), "w") as f:
            f.write('{"label": "Test Emu"}\n')
        with open(os.path.join(emu_dir, "subdir", "bin", "binary_tool"), "w") as f:
            f.write("binary data")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(emu_dir, arcname=sys_id)

        shutil.rmtree(source_dir, ignore_errors=True)
        return archive_path

    def test_safe_extract_fresh(self):
        """Test safe extraction into a fresh directory."""
        archive = self._create_test_archive("FRESH")
        ok, err = safe_extract_tar_gz(archive, paths.EMUS_DIR, "FRESH")
        self.assertTrue(ok, f"Extraction failed: {err}")
        self.assertTrue(os.path.isfile(os.path.join(paths.EMUS_DIR, "FRESH", "launch.sh")))
        self.assertTrue(os.path.isfile(os.path.join(paths.EMUS_DIR, "FRESH", "config.json")))
        self.assertTrue(os.path.isfile(os.path.join(paths.EMUS_DIR, "FRESH", "subdir", "bin", "binary_tool")))

    def test_safe_extract_over_existing_readonly(self):
        """Test extraction over existing files marked read-only (simulating FAT32 DOS flag)."""
        archive = self._create_test_archive("OVERWRITE")
        
        # Pre-create destination with read-only file
        dst_dir = os.path.join(paths.EMUS_DIR, "OVERWRITE")
        os.makedirs(dst_dir, exist_ok=True)
        launch_file = os.path.join(dst_dir, "launch.sh")
        with open(launch_file, "w") as f:
            f.write("old content")
        try:
            os.chmod(launch_file, 0o444)
        except OSError:
            pass

        ok, err = safe_extract_tar_gz(archive, paths.EMUS_DIR, "OVERWRITE")
        self.assertTrue(ok, f"Extraction failed on read-only file: {err}")
        with open(launch_file, "r") as f:
            content = f.read()
        self.assertIn("running", content)

    def test_safe_extract_path_traversal_protection(self):
        """Ensure path traversal attacks inside tar are rejected."""
        archive_path = os.path.join(self.tmp_dir, "MALICIOUS.tar.gz")
        evil_file = os.path.join(self.tmp_dir, "evil.txt")
        with open(evil_file, "w") as f:
            f.write("evil")

        with tarfile.open(archive_path, "w:gz") as tar:
            ti = tar.gettarinfo(evil_file, arcname="../../evil_escaped.txt")
            with open(evil_file, "rb") as f:
                tar.addfile(ti, f)

        ok, err = safe_extract_tar_gz(archive_path, paths.EMUS_DIR, "MALICIOUS")
        self.assertTrue(ok)
        escaped_file = os.path.abspath(os.path.join(paths.EMUS_DIR, "..", "evil_escaped.txt"))
        self.assertFalse(os.path.exists(escaped_file), "Path traversal vulnerability: file escaped target dir!")


if __name__ == "__main__":
    unittest.main()
