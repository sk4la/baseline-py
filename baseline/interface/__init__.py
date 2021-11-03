# Copyright (C) 2021  sk4la <sk4la.box@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import pathlib
import platform
import typing

__all__: list = []

ENVIRONMENT: typing.Dict[str, typing.Any] = {
    "node": platform.node(),
    "root": pathlib.Path.cwd().resolve(strict=True),
    "timestamp": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
}

PLATFORM_SPECIFIC_DEFAULTS: typing.Dict[str, typing.Dict[str, typing.Any]] = {
    "include": {
        "Linux": ["/"],
        "": [],
    },
    "exclude_directory": {
        "Linux": [
            "/dev",
            "/proc",
            "/run",
            "/tmp",
        ],
        "": [],
    },
    "exclude_extractor": {
        "Linux": [],
        "": [],
    },
    "log_file": {
        "Linux": (
            ENVIRONMENT.get("root") / f"{ENVIRONMENT['timestamp']}.{ENVIRONMENT['node']}.log"
        ),
        "": (ENVIRONMENT.get("root") / f"{ENVIRONMENT['timestamp']}.{ENVIRONMENT['node']}.log"),
    },
    "output_file": {
        "Linux": (
            ENVIRONMENT.get("root") / f"{ENVIRONMENT['timestamp']}.{ENVIRONMENT['node']}.ndjson"
        ),
        "": (ENVIRONMENT.get("root") / f"{ENVIRONMENT['timestamp']}.{ENVIRONMENT['node']}.ndjson"),
    },
    "output_file_encoding": {
        "Linux": "utf-8",
        "": "utf-8",
    },
}
SUPPORTED_ENCODINGS: typing.List[str] = ["utf-8", "utf-16le"]
