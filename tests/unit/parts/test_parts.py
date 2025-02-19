# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

from pathlib import Path
from unittest.mock import ANY, call

import craft_parts
import pytest

from snapcraft import errors
from snapcraft.parts import PartsLifecycle


@pytest.fixture
def parts_data():
    yield {
        "p1": {"plugin": "nil"},
    }


@pytest.mark.parametrize("step_name", ["pull", "overlay", "build", "stage", "prime"])
def test_parts_lifecycle_run(mocker, parts_data, step_name, new_dir, emitter):
    mocker.patch("craft_parts.executor.executor.Executor._install_build_snaps")
    lcm_spy = mocker.spy(craft_parts, "LifecycleManager")
    lifecycle = PartsLifecycle(
        parts_data,
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[],
        adopt_info=None,
        project_name="test-project",
        parse_info={},
        project_vars={"version": "1", "grade": "stable"},
        extra_build_snaps=["core22"],
    )
    lifecycle.run(step_name)
    assert lifecycle.prime_dir == Path(new_dir, "prime")
    assert lifecycle.prime_dir.is_dir()
    assert lcm_spy.mock_calls == [
        call(
            {"parts": {"p1": {"plugin": "nil"}}},
            application_name="snapcraft",
            work_dir=ANY,
            cache_dir=ANY,
            ignore_local_sources=["*.snap"],
            extra_build_packages=[],
            extra_build_snaps=["core22"],
            project_name="test-project",
            project_vars_part_name=None,
            project_vars={"version": "1", "grade": "stable"},
        )
    ]
    emitter.assert_progress(f"Executing parts lifecycle: {step_name} p1")


def test_parts_lifecycle_run_bad_step(parts_data, new_dir):
    lifecycle = PartsLifecycle(
        parts_data,
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[],
        adopt_info=None,
        parse_info={},
        project_name="test-project",
        project_vars={"version": "1", "grade": "stable"},
    )
    with pytest.raises(RuntimeError) as raised:
        lifecycle.run("invalid")
    assert str(raised.value) == "Invalid target step 'invalid'"


def test_parts_lifecycle_run_internal_error(parts_data, new_dir, mocker):
    lifecycle = PartsLifecycle(
        parts_data,
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[],
        adopt_info=None,
        project_name="test-project",
        parse_info={},
        project_vars={"version": "1", "grade": "stable"},
    )
    mocker.patch("craft_parts.LifecycleManager.plan", side_effect=RuntimeError("crash"))
    with pytest.raises(RuntimeError) as raised:
        lifecycle.run("prime")
    assert str(raised.value) == "Parts processing internal error: crash"


def test_parts_lifecycle_run_parts_error(new_dir):
    lifecycle = PartsLifecycle(
        {"p1": {"plugin": "dump", "source": "foo"}},
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[],
        adopt_info=None,
        project_name="test-project",
        parse_info={},
        project_vars={"version": "1", "grade": "stable"},
    )
    with pytest.raises(errors.PartsLifecycleError) as raised:
        lifecycle.run("prime")
    assert str(raised.value) == (
        "Failed to pull source: unable to determine source type of 'foo'."
    )


def test_parts_lifecycle_clean(parts_data, new_dir, emitter):
    lifecycle = PartsLifecycle(
        parts_data,
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[],
        adopt_info=None,
        project_name="test-project",
        parse_info={},
        project_vars={"version": "1", "grade": "stable"},
    )
    lifecycle.clean(part_names=None)
    emitter.assert_message("Cleaning all parts", intermediate=True)


def test_parts_lifecycle_clean_parts(parts_data, new_dir, emitter):
    lifecycle = PartsLifecycle(
        parts_data,
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[],
        adopt_info=None,
        project_name="test-project",
        parse_info={},
        project_vars={"version": "1", "grade": "stable"},
    )
    lifecycle.clean(part_names=["p1"])
    emitter.assert_message("Cleaning parts: p1", intermediate=True)


def test_parts_lifecycle_initialize_with_package_repositories(
    mocker,
    parts_data,
    new_dir,
):
    lcm_spy = mocker.spy(craft_parts, "LifecycleManager")
    PartsLifecycle(
        parts_data,
        work_dir=new_dir,
        assets_dir=new_dir,
        part_names=[],
        package_repositories=[
            {
                "type": "apt",
                "ppa": "test/somerepo",
            },
        ],
        adopt_info=None,
        project_name="test-project",
        parse_info={},
        project_vars={"version": "1", "grade": "stable"},
        extra_build_snaps=["core22"],
    )
    assert lcm_spy.mock_calls == [
        call(
            {"parts": {"p1": {"plugin": "nil"}}},
            application_name="snapcraft",
            work_dir=ANY,
            cache_dir=ANY,
            ignore_local_sources=["*.snap"],
            extra_build_packages=["gnupg", "dirmngr"],
            extra_build_snaps=["core22"],
            project_name="test-project",
            project_vars_part_name=None,
            project_vars={"version": "1", "grade": "stable"},
        )
    ]
