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

import dataclasses
import logging
import pathlib
import platform
import re
import typing

from baseline import errors, schema

__all__: typing.Tuple[str, ...] = (
    "kinds",
    "Extractor",
)


@dataclasses.dataclass(frozen=True)
class ObjectKind:
    FILE: int = 0
    DIRECTORY: int = 1
    SYMLINK: int = 2
    BLOCK_DEVICE: int = 3
    CHARACTER_DEVICE: int = 4
    FIFO: int = 5
    SOCKET: int = 6
    MOUNT: int = 7
    OTHER: int = 100

    @classmethod
    def humanize(cls: object, kind: int) -> str:
        return {
            cls.FILE: "file",
            cls.DIRECTORY: "directory",
            cls.SYMLINK: "symlink",
            cls.BLOCK_DEVICE: "block_device",
            cls.CHARACTER_DEVICE: "character_device",
            cls.FIFO: "fifo",
            cls.SOCKET: "socket",
            cls.MOUNT: "mount",
            cls.OTHER: "other",
        }.get(kind, "other")


kinds: ObjectKind = ObjectKind()


class Extractor:
    """This is an example."""

    EXTENSION_FILTERS: typing.Tuple[str, ...] = tuple()
    KEY: str = "example"
    KINDS: typing.Tuple[int, ...] = (
        kinds.FILE,
        kinds.DIRECTORY,
        kinds.SYMLINK,
        kinds.BLOCK_DEVICE,
        kinds.CHARACTER_DEVICE,
        kinds.FIFO,
        kinds.SOCKET,
        kinds.MOUNT,
        kinds.OTHER,
    )
    MAGIC_SIGNATURE_FILTERS: typing.Tuple[str, ...] = tuple()
    SYSTEM_FILTERS: typing.Tuple[str, ...] = tuple()

    @classmethod
    def is_compatible(cls: object) -> bool:
        return any(re.match(pattern, platform.system()) for pattern in cls.SYSTEM_FILTERS)

    @classmethod
    def supports(
        cls: object,
        entry: pathlib.Path,
        kind: int = kinds.FILE,
        magic_signature: typing.Optional[str] = None,
    ) -> bool:
        if kind not in cls.KINDS:
            return False

        filters: typing.List[bool] = [
            any(re.match(pattern, entry.suffix) for pattern in cls.EXTENSION_FILTERS),
        ]

        if magic_signature:
            filters.append(
                any(re.match(pattern, magic_signature) for pattern in cls.MAGIC_SIGNATURE_FILTERS),
            )

        return any(filters)

    def __init__(
        self: object,
        entry: pathlib.Path,
        kind: typing.Optional[int] = kinds.FILE,
        remap: typing.Dict[pathlib.Path, pathlib.Path] = {},
    ) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.entry: pathlib.Path = entry
        self.kind: typing.Optional[int] = kind
        self.remap: typing.Dict[pathlib.Path, pathlib.Path] = remap

    def run(self: object, record: schema.Record) -> None:
        raise errors.UnimplementedExtractorError(
            f"extractor `{self.__class__.__name__}` not implemented",
            name=self.__class__.__name__,
        )

    def remap_location(self: object, location: pathlib.Path) -> pathlib.Path:
        for source, destination in self.remap.items():
            try:
                location: pathlib.Path = destination / location.relative_to(source)

            except ValueError:
                pass

        return location
