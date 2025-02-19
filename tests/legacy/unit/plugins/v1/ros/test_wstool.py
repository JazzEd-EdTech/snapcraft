# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2018-2020 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import pathlib
import subprocess
from unittest import mock

import fixtures
from testtools.matchers import Contains, Equals

import snapcraft_legacy
from snapcraft_legacy.plugins.v1._ros import wstool
from tests.legacy import unit


class WstoolTestCase(unit.TestCase):
    def setUp(self):
        super().setUp()
        self.project = snapcraft_legacy.ProjectOptions()
        self.wstool = wstool.Wstool(
            "package_path", "wstool_path", self.project, "core18"
        )

        patcher = mock.patch("snapcraft_legacy.repo.Ubuntu")
        self.ubuntu_mock = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("subprocess.check_output")
        self.check_output_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def test_setup(self):
        # Return something other than a Mock to ease later assertions
        self.check_output_mock.return_value = b""

        self.wstool.setup()

        # Verify that only wstool was installed (no other .debs)
        self.assertThat(
            self.ubuntu_mock.fetch_stage_packages.mock_calls,
            Equals(
                [
                    mock.call(
                        stage_packages_path=self.wstool._wstool_stage_packages_path,
                        package_names=["python-wstool"],
                        base="core18",
                        target_arch=self.project.target_arch,
                    )
                ]
            ),
        )
        self.assertThat(
            self.ubuntu_mock.unpack_stage_packages.mock_calls,
            Equals(
                [
                    mock.call(
                        stage_packages_path=self.wstool._wstool_stage_packages_path,
                        install_path=pathlib.Path("wstool_path/install"),
                    )
                ]
            ),
        )

        # Verify that wstool was initialized
        self.check_output_mock.assert_called_once_with(
            ["wstool", "init", "package_path", "-j2"],
            env=mock.ANY,
            stderr=subprocess.PIPE,
        )

    def test_setup_can_run_multiple_times(self):
        self.wstool.setup()

        # Make sure running setup() again doesn't have problems with the old
        # environment. An exception will be raised if setup can't be called
        # twice.
        self.wstool.setup()

    def test_setup_initialization_rosinstall_already_exists(self):
        """Test that an existing .rosinstall file is not an error."""

        def run(args, **kwargs):
            if args[0:2] == ["wstool", "init"]:
                raise subprocess.CalledProcessError(
                    1,
                    "foo",
                    b"Error: There already is a workspace config file "
                    b'.rosinstall at ".". Use wstool install/modify.',
                )

        self.check_output_mock.side_effect = run

        self.wstool.setup()

    def test_setup_initialization_failure(self):
        def run(args, **kwargs):
            if args[0:2] == ["wstool", "init"]:
                raise subprocess.CalledProcessError(1, "foo", b"bar", b"baz")

        self.check_output_mock.side_effect = run

        raised = self.assertRaises(
            wstool.WorkspaceInitializationError, self.wstool.setup
        )

        self.assertThat(str(raised), Equals("Error initializing workspace: baz"))

    def test_merge(self):
        self.wstool.merge("rosinstall-file")

        self.check_output_mock.assert_called_with(
            ["wstool", "merge", "rosinstall-file", "--confirm-all", "-tpackage_path"],
            stderr=subprocess.PIPE,
            env=mock.ANY,
        )

    def test_merge_failure(self):
        def run(args, **kwargs):
            if args[0:2] == ["wstool", "merge"]:
                raise subprocess.CalledProcessError(1, "foo", b"bar", b"baz")

        self.check_output_mock.side_effect = run

        raised = self.assertRaises(
            wstool.RosinstallMergeError, self.wstool.merge, "rosinstall-file"
        )

        self.assertThat(
            str(raised),
            Equals(
                "Error merging rosinstall file 'rosinstall-file' into workspace: baz"
            ),
        )

    def test_update(self):
        self.wstool.update()

        self.check_output_mock.assert_called_with(
            ["wstool", "update", "-j2", "-tpackage_path"],
            env=mock.ANY,
            stderr=subprocess.PIPE,
        )

    def test_update_failure(self):
        def run(args, **kwargs):
            if args[0:2] == ["wstool", "update"]:
                raise subprocess.CalledProcessError(1, "foo", b"bar", b"baz")

        self.check_output_mock.side_effect = run

        raised = self.assertRaises(wstool.WorkspaceUpdateError, self.wstool.update)

        self.assertThat(str(raised), Equals("Error updating workspace: baz"))

    def test_run(self):
        wstool = self.wstool

        # Create a single library directory for asserting LD_LIBRARY_PATH is set
        # properly.
        os.makedirs(os.path.join(wstool._wstool_install_path, "lib"))

        self.useFixture(fixtures.EnvironmentVariable("LD_LIBRARY_PATH", None))

        wstool._run(["init"])

        class check_env:
            def __init__(self, test):
                self.test = test

            def __eq__(self, env):
                for variable in (
                    "PATH",
                    "LD_LIBRARY_PATH",
                    "GIT_EXEC_PATH",
                    "PYTHONPATH",
                ):
                    self.test.assertThat(env, Contains(variable))

                self.test.assertThat(
                    env["PATH"],
                    Equals(
                        "{}:{}".format(
                            os.environ["PATH"],
                            os.path.join(wstool._wstool_install_path, "usr", "bin"),
                        )
                    ),
                )

                self.test.assertThat(
                    env["LD_LIBRARY_PATH"],
                    Equals(
                        "{}".format(os.path.join(wstool._wstool_install_path, "lib"))
                    ),
                )

                self.test.assertThat(
                    env["GIT_EXEC_PATH"],
                    Equals(
                        os.path.join(
                            wstool._wstool_install_path, "usr", "lib", "git-core"
                        )
                    ),
                )

                self.test.assertThat(
                    env["PYTHONPATH"],
                    Equals(
                        os.path.join(
                            wstool._wstool_install_path,
                            "usr",
                            "lib",
                            "python2.7",
                            "dist-packages",
                        )
                    ),
                )

                return True

        self.check_output_mock.assert_called_with(
            mock.ANY, env=check_env(self), stderr=subprocess.PIPE
        )
