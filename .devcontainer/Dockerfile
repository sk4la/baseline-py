# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.202.3/containers/python-3/.devcontainer/base.Dockerfile

ARG VARIANT

FROM "mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}" AS development

RUN python3 -m pip --disable-pip-version-check --no-cache-dir install \
        poetry

RUN apt-get update && \
    DEBIAN_FRONTEND="noninteractive" \
    apt-get --yes install --no-install-recommends \
        build-essential \
        chrpath \
        libffi-dev \
        libfuzzy-dev \
        make
