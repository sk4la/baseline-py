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

import collections
import math
import typing

__all__: list = []


def compute_shannon_entropy(stream: typing.IO[bytes], buffer_size: int = 4096) -> float:
    entropy: float = 0.0
    size: int = 0

    byte_frequency_counter: collections.Counter = collections.Counter()

    while chunk := stream.read(buffer_size):
        byte_frequency_counter.update(chunk)
        size += len(chunk)

    for byte_frequency in byte_frequency_counter.values():
        byte_probability: float = byte_frequency / size

        if byte_probability:
            entropy += -byte_probability * math.log(byte_probability, 2)

    return round(entropy, 6)
