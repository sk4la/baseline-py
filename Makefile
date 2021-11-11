#!/usr/bin/env make --file

DOCKER_REGISTRY?=docker.io

POETRY_VERSION?=1.1.7

PRODUCT_BUILD_COMMIT:=$(shell git log --max-count=1 --pretty=format:%H)
PRODUCT_BUILD_DATE:=$(shell date --iso-8601)
PRODUCT_NAME=baseline
PRODUCT_REPOSITORY=https://github.com/sk4la/baseline
PRODUCT_VERSION?=0.1.2

PYPI_USERNAME?=__token__
PYPI_PASSWORD?=

PYTHON_PACKAGE_NAME?="${PRODUCT_NAME}"
PYTHON_VERSION?=3.9

SOURCE_DIRECTORY="${PRODUCT_NAME}"

define HELP_MENU
Usage: make <env> <target> <target>...

Main targets:
  all                 Call the default targets. [bootstrap]
  bootstrap           Install the development environment.
  help                Show this help.

Development targets:
  format              Format the source code using black and isort.
  install             Install the project.
  lint                Lint the source code using flake8.

Release targets:
  docker              Build the Docker image.
  nuitka-linux        Build the standalone binary for GNU/Linux.
  pyinstaller-linux   Build the standalone binary for GNU/Linux.
  pypi                Build and publish the package to PyPI.

Refer to the documentation for use cases and examples.
endef

.PHONY: all bootstrap docker format help install lint nuitka-linux pyinstaller-linux pypi

all: help

bootstrap:
	@python3 -m pip install \
		poetry

	@python3 -m poetry install \
		--no-ansi \
		--no-interaction

docker:
	@docker build \
		--build-arg="POETRY_VERSION=${POETRY_VERSION}" \
		--build-arg="PRODUCT_BUILD_COMMIT=${PRODUCT_BUILD_COMMIT}" \
		--build-arg="PRODUCT_BUILD_DATE=${PRODUCT_BUILD_DATE}" \
		--build-arg="PRODUCT_REPOSITORY=${PRODUCT_REPOSITORY}" \
		--build-arg="PRODUCT_VERSION=${PRODUCT_VERSION}" \
		--build-arg="PYTHON_VERSION=${PYTHON_VERSION}" \
		--tag="${DOCKER_REGISTRY}/sk4la/${PRODUCT_NAME}:${PRODUCT_VERSION}" \
		--tag="${DOCKER_REGISTRY}/sk4la/${PRODUCT_NAME}:latest" \
		.

format:
	@python3 -m black \
		"$(SOURCE_DIRECTORY)"

	@python3 -m isort \
		"$(SOURCE_DIRECTORY)"

help:
	$(info $(HELP_MENU))

install:
	@python3 -m poetry install \
		--no-ansi \
		--no-dev \
		--no-interaction

lint:
	@python3 -m flake8 \
		--max-line-length=99 \
		"$(SOURCE_DIRECTORY)/"

nuitka-linux:
	@python3 -m nuitka \
	    -o="$(PYTHON_PACKAGE_NAME)" \
		--assume-yes-for-downloads \
		--include-package="$(PYTHON_PACKAGE_NAME)" \
		--onefile \
		--prefer-source-code \
		--python-flag=no_site,no_warnings,no_asserts,no_docstrings \
		--remove-output \
		--show-progress \
		--standalone \
		--warn-implicit-exceptions \
		--warn-unusual-code \
		"$(SOURCE_DIRECTORY)"

pyinstaller-linux:
	@pyinstaller \
		--add-data=LICENSE:LICENSE \
		--copy-metadata="$(PYTHON_PACKAGE_NAME)" \
		--name="$(PYTHON_PACKAGE_NAME)" \
		--noconfirm \
		--onefile \
		--strip \
		"$(SOURCE_DIRECTORY)/__main__.py"

pypi:
	@python3 -m poetry publish \
		--build
