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

ARG PYTHON_VERSION

FROM "docker.io/library/python:${PYTHON_VERSION}-bullseye" AS production

ARG POETRY_VERSION

ARG PRODUCT_BUILD_COMMIT
ARG PRODUCT_BUILD_DATE
ARG PRODUCT_REPOSITORY
ARG PRODUCT_VERSION

ENV LANG="C.UTF-8"
ENV LC_ALL="C.UTF-8"

ENV POETRY_VIRTUALENVS_CREATE="false"

ENV PYTHONFAULTHANDLER="1"
ENV PYTHONHASHSEED="random"
ENV PYTHONUNBUFFERED="1"

RUN apt-get update && \
    DEBIAN_FRONTEND="noninteractive" \
    apt-get --yes install --no-install-recommends \
        libffi-dev \
        libfuzzy-dev \
        make

RUN python3 -m pip --disable-pip-version-check --no-cache-dir install \
        "poetry==${POETRY_VERSION}"

COPY --chown=root:root . /opt/baseline

WORKDIR /opt/baseline

RUN make install

ENTRYPOINT [ "baseline" ]

CMD [ "--help" ]

LABEL image.commit="${PRODUCT_BUILD_COMMIT}"
LABEL image.date="${PRODUCT_BUILD_DATE}"
LABEL image.repository="${PRODUCT_REPOSITORY}"
LABEL image.version="${PRODUCT_VERSION}"
