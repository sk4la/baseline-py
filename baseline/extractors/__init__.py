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

import logging
import typing

from baseline import models
from baseline.extractors import executables, filesystem

__all__: typing.Tuple[str, ...] = ("iterate_extractors",)


def iterate_extractors(
    exclude: typing.List[str] = [],
) -> typing.Iterator[models.Extractor]:
    for extractor in models.Extractor.__subclasses__():
        if extractor.is_compatible:
            if extractor.KEY in exclude:
                logger: logging.Logger = logging.getLogger(__name__)
                logger.debug("Ignoring excluded extractor `%s`.", extractor.KEY)

                continue

            yield extractor
