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
import hashlib
import pathlib
import sys
import typing
import warnings

import ssdeep

from baseline import models, schema
from baseline.extractors import common

__all__: typing.Tuple[str, ...] = (
    "Metadata",
    "Hashes",
)


class Metadata(models.Extractor):
    """Extracts filesystem-related metadata"""

    EXTENSION_FILTERS = (r".*",)
    KEY = "fs"
    KINDS = (
        models.kinds.FILE,
        models.kinds.DIRECTORY,
        models.kinds.SYMLINK,
        models.kinds.BLOCK_DEVICE,
        models.kinds.CHARACTER_DEVICE,
        models.kinds.FIFO,
        models.kinds.SOCKET,
        models.kinds.MOUNT,
        models.kinds.OTHER,
    )
    MAGIC_SIGNATURE_FILTERS = (r".*",)
    SYSTEM_FILTERS = (r"^Linux$",)

    def run(self: object, record: schema.Record) -> None:
        try:
            # This only works when baselining an active system. It will return `KeyError` when
            # baselining a mounted image that contains foreign GIDs for example. In that case, the
            # associated fields will be `None` (`null` in JSON).
            group: typing.Optional[str] = self.entry.group()

        except KeyError:
            group: typing.Optional[str] = None

        try:
            # This only works when baselining an active system. It will return `KeyError` when
            # baselining a mounted image that contains foreign GIDs for example. In that case, the
            # associated fields will be `None` (`null` in JSON).
            user: typing.Optional[str] = self.entry.owner()

        except KeyError:
            user: typing.Optional[str] = None

        try:
            stats = self.entry.stat(
                follow_symlinks=self.kind != models.kinds.SYMLINK,
            )

        except TypeError:
            if sys.version_info >= (3, 10):
                raise

            warnings.warn(
                "The `follow_symlinks` parameter was only added to `pathlib.Path.stat` in Python "
                "3.10 so it cannot be used with the current installation of Python ("
                f"{'.'.join(str(component) for component in sys.version_info[:3])}). Update your "
                "installation to remove this warning. Falling back to the old way (following all "
                "symlinks)."
            )

            stats = self.entry.stat()

        location = self.remap_location(self.entry)

        setattr(
            record,
            self.KEY,
            schema.FilesystemMetadata(
                extension=location.suffix or None,
                name=location.name,
                parent=schema.Parent(
                    path=str(location.parent),
                ),
                path=str(location),
                permissions=schema.Permissions(
                    mode=str(oct(stats.st_mode)),
                    ownership=schema.Ownership(
                        gid=stats.st_gid,
                        group=group,
                        uid=stats.st_uid,
                        user=user,
                    ),
                ),
                size=stats.st_size,
                target=str(self.entry.readlink()) if self.kind == models.kinds.SYMLINK else None,
                timestamps=schema.Timestamps(
                    atime=datetime.datetime.utcfromtimestamp(stats.st_atime).isoformat(),
                    ctime=datetime.datetime.utcfromtimestamp(stats.st_ctime).isoformat(),
                    mtime=datetime.datetime.utcfromtimestamp(stats.st_mtime).isoformat(),
                ),
            ),
        )

        self.logger.debug("Extracted filesystem metadata from entry `%s`.", self.entry)


class Hashes(models.Extractor):
    """Computes several hashes from the entry's data (e.g. MD5, SHA-1, ssdeep)."""

    EXTENSION_FILTERS = (r".*",)
    KEY = "hash"
    KINDS = (models.kinds.FILE,)
    MAGIC_SIGNATURE_FILTERS = (r".*",)
    SYSTEM_FILTERS = (r"^Linux$",)

    def run(self: object, record: schema.Record) -> None:
        setattr(
            record,
            self.KEY,
            schema.HashDigests(
                entropy=self._compute_entropy(self.entry),
                md5=self._compute_hash(self.entry),
                sha1=self._compute_hash(self.entry, hash_algorithm="sha1"),
                sha256=self._compute_hash(self.entry, hash_algorithm="sha256"),
                ssdeep=self._compute_fuzzy_hash(self.entry),
            ),
        )

    def _compute_entropy(self: object, entry: pathlib.Path) -> float:
        with entry.open("rb") as stream:
            entropy: float = common.compute_shannon_entropy(stream)

            self.logger.debug("Computed Shannon entropy of file `%s`.", entry)

            return entropy

    def _compute_fuzzy_hash(
        self: object,
        entry: pathlib.Path,
        buffer_size: int = 4096,
    ) -> str:
        with entry.open("rb") as stream:
            cipher = ssdeep.Hash()

            while chunk := stream.read(buffer_size):
                cipher.update(chunk)

            digest: str = cipher.digest()

            self.logger.debug("Computed `ssdeep` fuzzy hash digest of file `%s`.", entry)

            return digest

    def _compute_hash(
        self: object,
        entry: pathlib.Path,
        hash_algorithm: str = "md5",
        buffer_size: int = 4096,
    ) -> str:
        with entry.open("rb") as stream:
            cipher = getattr(hashlib, hash_algorithm)()

            while chunk := stream.read(buffer_size):
                cipher.update(chunk)

            digest: str = cipher.hexdigest()

            self.logger.debug("Computed `%s` hash digest of file `%s`.", hash_algorithm, entry)

            return digest
