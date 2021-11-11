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

__all__: typing.Tuple[str, ...] = (
    "GenericError",
    "ImplementationError",
    "ValidationError",
)


class BaseException(Exception):
    def __init__(
        self: object,
        message: typing.Optional[str],
        context: typing.Optional[typing.Dict[str, typing.Any]],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        self.message: typing.Optional[str] = message
        self.context: typing.Optional[typing.Dict[str, typing.Any]] = context

        super().__init__(*args, **kwargs)


class GenericError(BaseException):
    ...


class ImplementationError(BaseException):
    ...


class ValidationError(BaseException):
    ...
