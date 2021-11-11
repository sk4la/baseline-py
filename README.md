<div align="center">
  <br />
  <img src="assets/logo_dark.png" width="600" />
  <br />
  <br />
  <img src="https://img.shields.io/static/v1?label=code%20style&message=black&color=black&style=flat-square"/>
  <img src="https://img.shields.io/static/v1?label=version&message=0.1.3&color=orange&style=flat-square"/>
  <img src="https://img.shields.io/static/v1?label=python&message=3.10&color=blueviolet&style=flat-square"/>
  <img src="https://img.shields.io/static/v1?label=license&message=GPLv3&color=brightgreen&style=flat-square"/>
</div>

# Baselining, on steroids!

Baseline is a cross-platform library and command-line utility that creates file-oriented baselines of your systems.

The project aims to offer an open-source alternative to the famous [NSRL](https://www.nist.gov/itl/ssd/software-quality-group/national-software-reference-library-nsrl) or [HashSets](https://www.hashsets.com/) and allows you to generate baselines from your own systems. Plus, it is cross-platform, so you can use it the same way whether on a Windows or a GNU/Linux system.

Currently available [extractors](baseline/extractors):

- `fs`: Extracts filesystem-related metadata.
- `hash`: Computes several hashes from the entry's data (e.g. MD5, SHA-1, ssdeep).
- `pe`: Extracts detailed information from Portable Executable (PE) files.

## Table of contents

- [Installation](#installation)
  - [Installing from PyPI](#installing-from-pypi)
  - [Installing from source](#installing-from-source)
  - [Precompiled binaries](#precompiled-binaries)
- [Usage](#usage)
  - [Creating a baseline of a live system](#creating-a-baseline-of-a-live-system)
  - [Creating a baseline from a mounted image](#creating-a-baseline-from-a-mounted-image)
  - [Displaying the schema](#displaying-the-schema)
- [Advanced usage](#usage)
  - [Building binaries](#building-binaries)
- [API](#library)
- [Contribute](#contribute)
  - [Writing a new extractor](#writing-a-new-extractor)
- [Support](#support)
- [License](#license)

## Installation

### Installing from PyPI

Baseline is currently not available on PyPI. The main reason is that the name is currently taken by [another project](https://github.com/dmgass/baseline).

### Installing from source

Since Baseline uses [Poetry](https://python-poetry.org/) as its packaging toolkit of choice, so installing it from source is as simple as:

```shell
git clone httpe://github.com/sk4la/baseline.git
cd baseline

python3 -m pip install poetry
python3 -m poetry install
```

### Precompiled binaries

Precompiled binaries are available in the [Releases](https://github.com/sk4la/baseline/releases) section.

### Docker

Baseline is also available as a [Docker image](https://hub.docker.com/r/sk4la/baseline).

To pull the latest image from Docker Hub:

```shell
docker pull sk4la/baseline
```

> See the [official Docker documentation](https://docs.docker.com/get-docker/) for details on how to install and use it.

## Usage

The help menu for the `baseline` command-line utility:

```text
Usage: baseline <options> COMMAND [ARGS]...

  Command-line utility that creates file-oriented baselines.

Options:
  --ensure-administrator          Ensure that the current user has administrative privileges (i.e.
                                  is `root` or equivalent on GNU/Linux systems).
  --log-file <file>               Set the log file path (e.g. 'baseline.log').  [default:
                                  /home/sk4la/baseline/20211031110323.25756fb1b706.log]
  --logging-configuration <file>  Set the logging configuration using a custom file. The file must
                                  adhere to the official specification. See
                                  https://docs.python.org/3/library/logging.config.html#logging-
                                  config-dictschema for more details.
  --monochrome                    Disable console output coloring. This can be useful when piping
                                  the output to a log file.
  -v, --verbose                   Increase the logging verbosity. Supports up to 4 occurrences of
                                  the same option (e.g. -vvvv).  [0<=x<=4]
  --version                       Show the version and exit.
  --help                          Show this message and exit.

Commands:
  new     Creates a new filesystem-based baseline.
  schema  Show the JSON representation of the actual schema.
```

The help menu for the `baseline new` subcommand:

```text
Usage: baseline new <options> <path>...

  Creates a new filesystem-based baseline.

Options:
  --comment <str>                 Add an arbitrary comment to the generated output file.
  --exclude-directory <directory>...
                                  Exclude a specific directory from the baseline. Can be specified
                                  multiple times (e.g. `--exclude-directory /dev --exclude-
                                  directory /proc`).
  --exclude-extractor [hash|pe|fs]
                                  Exclude extractors. Can be specified multiple times (e.g.
                                  `--exclude-extractor hash --exclude-extractor pe`).
  --max-size <int>                Set the maximum file size (in bytes) to inspect.  [default:
                                  5000000; x>=1]
  -o, --output-file <file>        Set the output file path (e.g. 'baseline.ndjson').  [default:
                                  /workspaces/baseline/20211102200452.58bd60a3b16a.ndjson]
  --output-file-encoding [utf-8|utf-16le]
                                  Set the output file encoding. Only applies when writing to an
                                  actual file.  [default: utf-8]
  -f, --output-format [ndjson]    Set the output format.  [default: ndjson]
  --partition-size <int>          Set the partition size (i.e. number of entries per process).
                                  [default: 200; x>=1]
  --processes <int>               Set the number of parallel processes.  [default: 2; x>=1]
  --recursive / --non-recursive   Whether to walk the filesystem recursively. When set, the
                                  program will only inspect the files and directories specifies on
                                  the first level of any included path. For example, if
                                  '/mnt/image' is specified as an included path, then only the
                                  directory '/mnt/image' itself and its direct children will be
                                  inspected.  [default: recursive]
  --remap <key:value>...          Artificially remap included paths (e.g. '/mnt/image:/'). Can be
                                  specified multiple times (e.g. `--remap /mnt/image:/ --remap
                                  /dev/null:/dev/void`).
  --report / --no-report          Whether to show a final report at the end.  [default: report]
  --skip-compression              Whether to skip on-the-fly compression of the resulting file.
  --skip-directories              Whether to skip directories.
  --skip-empty                    Whether to skip empty entries.
  --help                          Show this message and exit.
```

The help menu for the `baseline schema` subcommand:

```text
Usage: baseline schema <options>

  Show the JSON representation of the actual schema.

Options:
  --compact                       Render compact JSON instead of the default indented version.
  --output-file <file>            Set the output file path (e.g. 'schema.json').
  --output-file-encoding [utf-8|utf-16le]
                                  Set the output file encoding. Only applies when writing to an
                                  actual file.  [default: utf-8]
  --help                          Show this message and exit.
```

### Creating a baseline of a live system

Creating a baseline of a live system is as simple as:

```shell
baseline new
```

When using Baseline from a removable device, you may want to exclude its path (for example `/mnt/usb`) from the generated baseline:

```shell
baseline --ensure-administrator new --exclude-directory /mnt/usb
```

See the [Usage](#usage) section for a complete list of options and arguments.

### Creating a baseline from a mounted image

When creating a baseline of a mounted image, you may want the baseline to represent the files as if they were read from the actual system, not the mounted image.

For example, if your image is currently mounted on `/mnt/IMG-001`, you can then execute the following command to remap all entries read from this path to `/`:

```shell
baseline new --remap /mnt/IMG-001:/ /mnt/IMG-001
```

You can think of this as a chroot jail.

### Displaying the schema

Baseline uses a fixed schema for rendering the information. This schema is enforced using the [Pydantic](https://pydantic-docs.helpmanual.io/) package and produces a heavily-typed output that can later be ingested as-is.

To print the standardized JSON schema:

```shell
baseline schema
```

To dump a compact version of the JSON schema to `schema.min.json`:

```shell
baseline schema --compact --output-file schema.min.json
```

The JSON schema produced by Pydantic is compatible with the specifications from [JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core.html), [JSON Schema Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html) and [OpenAPI Data Types](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.2.md#data-types). See the official [Pydantic documentation](https://pydantic-docs.helpmanual.io/usage/schema/#json-schema-types) for more details.

## Advanced usage

### Building binaries

Baseline currently supports the following packaging systems:

* [PyInstaller](https://www.pyinstaller.org/index.html) (preferred) ;
* [Nuitka](https://nuitka.net/pages/overview.html).

> Although precompiled binaries are available in the [Releases](https://github.com/sk4la/baseline/releases) section, you should always build your own binaries.

To produce a binary using PyInstaller:

```shell
make pyinstaller-linux
```

To produce a binary using Nuitka:

```shell
make nuitka-linux
```

As Nuitka is a Python compiler by itself and does not rely on the standard CPython interpreter, you should be aware that there may be bugs and/or issues unrelated to Baseline itself.

### Building the Docker image

To build the official Docker image:

```shell
make docker
```

Additional instructions can be added to the `Dockerfile` in order to customize the image.

> The official Docker image is available at https://hub.docker.com/r/sk4la/baseline. You can use the `FROM docker.io/sk4la/baseline:latest` instruction in your own `Dockerfile` to derive your own image.

## API

Using Baseline from Python is possible using the [`Baseline`](baseline/core.py) class:

```python
from baseline.core import Baseline

with Baseline() as baseline:
    for record in baseline.compute(*[
        "/mnt/IMG-001",
        "/mnt/IMG-002",
    ]):
        print(record.json(exclude_none=True))
```

See the [actual code](baseline/interface/root.py) for a more thorough example.

> The [`Baseline`](baseline/core.py) class emits logging messages to the `baseline` logger, to which you can subscribe to if you wish. The command-line utility displays these messages to the console by default.

## Contribute

Baseline is a work in progress, everyone is welcome to contribute! 👐

### Writing a new extractor

In order for new extractors to be able to enrich the generated records, the global schema first needs to be updated. To do this, you must create a sublass of Pydantic's [`BaseModel`](https://pydantic-docs.helpmanual.io/usage/models/#basic-model-usage) in [`schema.py`](`baseline/schema.py`) that references the fields that will eventually be filled by the extractor. This class will then be referenced in the schema's root `Record` class.

In this example, we want to extract the first 50 lines of any `*.txt` file. Here we arbitrarily decide that the extracted text will be stored in the `content` attribute and that the extractor's key will be `text`:

```python
class Text(pydantic.BaseModel):
    content: str

class Record(pydantic.BaseModel):
    ...
    text: typing.Optional[Text]
```

We can then start to write the actual code. All extractors must inherit from the base `Extractor` class:

```python
from baseline.models import Extractor
from baseline.schema import Text

class Text(Extractor):
    """Extracts the first line of any `.txt` file."""

    EXTENSION_FILTERS = (
      r"\.txt$",
    )
    KEY = "text"

    def run(self: object, record: schema.Record) -> None:
        with self.entry.open() as stream:
            setattr(
                record,
                self.KEY,
                schema.Text(
                    content=stream.read(50),
                ),
            )
```

The extractor's `KEY` class variable must correspond to the one that was specified in the schema's root `Record` class (`text` in this example).

## Support

In case you encounter a problem or want to suggest a new feature, please [submit a ticket](https://github.com/sk4la/baseline/issues).

## License

Baseline is licensed under the [GNU General Public License (GPL) version 3](LICENSE).
