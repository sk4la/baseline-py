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

import typing

import pydantic

import baseline

__all__: typing.Tuple[str, ...] = (
    "HashDigests",
    "FilesystemMetadata",
    "Ownership",
    "Parent",
    "Permissions",
    "PortableExecutable",
    "PortableExecutableResource",
    "PortableExecutableSection",
    "Record",
    "Signature",
    "Timestamps",
    "Version",
)


class HashDigests(pydantic.BaseModel):
    entropy: pydantic.confloat(ge=0.0)
    md5: str
    sha1: str
    sha256: str
    ssdeep: str


class Ownership(pydantic.BaseModel):
    gid: typing.Optional[pydantic.conint(ge=0)]
    group: typing.Optional[str]
    uid: typing.Optional[pydantic.conint(ge=0)]
    user: typing.Optional[str]


class Parent(pydantic.BaseModel):
    path: typing.Optional[str]


class Permissions(pydantic.BaseModel):
    mode: typing.Optional[str]
    ownership: typing.Optional[Ownership]


class Timestamps(pydantic.BaseModel):
    atime: typing.Optional[str]
    ctime: typing.Optional[str]
    mtime: typing.Optional[str]


class FilesystemMetadata(pydantic.BaseModel):
    path: typing.Optional[str]
    name: typing.Optional[str]
    extension: typing.Optional[str]
    parent: typing.Optional[Parent]
    permissions: typing.Optional[Permissions]
    size: typing.Optional[pydantic.conint(ge=0)]
    target: typing.Optional[str]
    timestamps: typing.Optional[Timestamps]


class PortableExecutableSection(pydantic.BaseModel):
    entropy: typing.Optional[pydantic.confloat(ge=0.0)]
    name: typing.Optional[str]
    psize: typing.Optional[pydantic.conint(ge=0)]
    vsize: typing.Optional[pydantic.conint(ge=0)]


class PortableExecutableResource(pydantic.BaseModel):
    identifier: typing.Optional[pydantic.PositiveInt]
    name: typing.Optional[str]


class PortableExecutable(pydantic.BaseModel):
    exports: typing.Optional[typing.List[str]]
    imports: typing.Optional[typing.List[str]]
    sections: typing.Optional[typing.List[PortableExecutableSection]]


class Version(pydantic.BaseModel):
    package: typing.Optional[str] = baseline.__version__
    model: typing.Optional[str] = baseline.SCHEMA_VERSION


class Signature(pydantic.BaseModel):
    kind: str
    magic: typing.Optional[str]
    mime: typing.Optional[str]


class Record(pydantic.BaseModel):
    comment: typing.Optional[str]
    signature: Signature
    version: Version = Version()
    fs: typing.Optional[FilesystemMetadata]
    hash: typing.Optional[HashDigests]
    pe: typing.Optional[PortableExecutable]
