# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015 Canonical Ltd
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

from snapcraft_legacy import BasePlugin


class LocalPlugin(BasePlugin):
    @classmethod
    def schema(cls):
        schema = super().schema()

        schema["properties"]["foo"] = {"type": "string"}

        return schema

    @classmethod
    def get_pull_properties(cls):
        return ["foo", "stage-packages"]

    @classmethod
    def get_build_properties(cls):
        return ["foo", "stage-packages"]

    def build(self):
        return self.run(["touch", "build-stamp"], self.installdir)
