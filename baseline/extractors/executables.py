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

import io
import logging
import pathlib
import typing

import pefile

from baseline import errors, models, schema
from baseline.extractors import common

__all__: typing.Tuple[str, ...] = ("PortableExecutable",)


class PortableExecutable(models.Extractor):
    """Extracts detailed information from Portable Executable (PE) files."""

    EXTENSION_FILTERS = (
        r"\.acm$",
        r"\.ax$",
        r"\.cpl$",
        r"\.dll$",
        r"\.drv$",
        r"\.efi$",
        r"\.exe$",
        r"\.mui$",
        r"\.ocx$",
        r"\.scr$",
        r"\.sys$",
        r"\.tsp$",
    )
    KEY = "pe"
    KINDS = (models.kinds.FILE,)
    MAGIC_SIGNATURE_FILTERS = (r"^PE32(\+) executable",)
    SYSTEM_FILTERS = (r"^Linux$",)

    def __init__(
        self: object,
        entry: pathlib.Path,
        kind: int = models.kinds.FILE,
        remap: typing.Dict[pathlib.Path, pathlib.Path] = {},
    ) -> None:
        self.logger = logging.getLogger(__name__)

        self.entry = entry
        self.kind = kind
        self.remap = remap

        try:
            self.executable: pefile.PE = pefile.PE(self.entry, fast_load=True)

        except pefile.PEFormatError as exception:
            self.logger.exception(
                "Failed to load file `%s` (%s).",
                self.entry,
                models.kinds.humanize(self.kind),
            )

            raise errors.GenericError(
                f"failed to load file {self.entry}",
                self.entry,
                models.kinds.humanize(self.kind),
            ) from exception

    def __del__(self: object) -> None:
        self.executable.close()

    def run(self: object, record: schema.Record) -> None:
        setattr(
            record,
            self.KEY,
            schema.PortableExecutable(
                exports=list(self._get_exports(self.executable)),
                imports=list(self._get_imports(self.executable)),
                resources=list(self._get_resources(self.executable)),
                sections=list(self._get_sections(self.executable)),
            ),
        )

    def _get_exports(self: object, executable: pefile.PE) -> typing.Iterator[str]:
        executable.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]],
        )

        count: int = 0

        if directory := getattr(executable, "DIRECTORY_ENTRY_EXPORT", None):
            for entry in directory.symbols:
                count += 1
                yield entry.name.decode("utf-8")

        self.logger.debug(
            "Extracted `%d` exports from Portable Executable file `%s`.",
            count,
            self.entry,
        )

    def _get_imports(self: object, executable: pefile.PE) -> typing.Iterator[str]:
        executable.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]],
        )

        count: int = 0

        if directory := getattr(executable, "DIRECTORY_ENTRY_IMPORT", None):
            for table in directory:
                for entry in table.imports:
                    count += 1

                    if entry.name:
                        yield entry.name.decode("utf-8")

        self.logger.debug(
            "Extracted `%d` imports from Portable Executable file `%s`.",
            count,
            self.entry,
        )

    def _get_resources(
        self: object,
        executable: pefile.PE,
    ) -> typing.Iterator[schema.PortableExecutableResource]:
        executable.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]],
        )

        count: int = 0

        if directory := getattr(executable, "DIRECTORY_ENTRY_RESOURCE", None):
            for entry in directory.entries:
                count += 1

                yield schema.PortableExecutableResource(
                    identifier=entry.id,
                    name=entry.name,
                )

        self.logger.debug(
            "Extracted `%d` resources from Portable Executable file `%s`.",
            count,
            self.entry,
        )

    def _get_sections(
        self: object,
        executable: pefile.PE,
    ) -> typing.Iterator[schema.PortableExecutableSection]:
        count: int = 0

        for section in executable.sections:
            count += 1

            yield schema.PortableExecutableSection(
                entropy=common.compute_shannon_entropy(io.BytesIO(section.get_data())),
                name=section.Name.decode("utf-8").rstrip("\u0000"),
                psize=section.SizeOfRawData,
                vsize=section.Misc_VirtualSize,
            )

        self.logger.debug(
            "Extracted `%d` sections from Portable Executable file `%s`.",
            count,
            self.entry,
        )
