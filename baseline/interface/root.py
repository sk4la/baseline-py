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

import abc
import datetime
import functools
import getpass
import json
import locale
import logging
import logging.config
import lzma
import operator
import os
import pathlib
import platform
import sys
import time
import typing

import click
import click_help_colors
import hfilesize
import jinja2
import psutil
import pydantic
import pydantic.schema
import rich
import rich.logging

import baseline
from baseline import core, errors, extractors, interface, schema

__all__: list = []


def ensure_administrator(
    _context: click.core.Context,
    _parameter: click.core.Parameter,
    value: str,
) -> None:
    if value and (uid := (os.getuid() or os.geteuid())):
        raise click.ClickException(
            f"The current user (uid {uid}) does not have administrative privileges (i.e. `root` "
            "or equivalent). Try launching the program using `sudo` or removing the "
            "`--ensure-administrator` flag if the target does not need administrator privileges "
            "to be accessed.",
        )


@click.group(
    cls=click_help_colors.HelpColorsGroup,
    context_settings={
        "max_content_width": 100,
    },
    help_headers_color="yellow",
    help_options_color="green",
    help=baseline.retrieve_package_metadata("Summary", None),
    name=baseline.__package__,
    options_metavar="<options>",
)
@click.option(
    "--ensure-administrator",
    callback=ensure_administrator,
    help=(
        "Ensure that the current user has administrative privileges (i.e. is `root` or equivalent "
        "on GNU/Linux systems)."
    ),
    is_flag=True,
    type=click.UNPROCESSED,
)
@click.option(
    "--log-file",
    help="Set the log file path (e.g. 'baseline.log').",
    default=interface.PLATFORM_SPECIFIC_DEFAULTS["log_file"].get(platform.system()),
    metavar="<file>",
    show_default=True,
    type=click.Path(
        dir_okay=False,
        resolve_path=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "--logging-configuration",
    help=(
        "Set the logging configuration using a custom file. The file must adhere to the official "
        "specification. See "
        "https://docs.python.org/3/library/logging.config.html#logging-config-dictschema for more "
        "details."
    ),
    metavar="<file>",
    type=click.Path(
        exists=True,
        dir_okay=False,
        resolve_path=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "--monochrome",
    help=(
        "Disable console output coloring. This can be useful when piping the output to a log file."
    ),
    is_flag=True,
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help=(
        "Increase the logging verbosity. Supports up to 4 occurrences of the same option (e.g. "
        "-vvvv)."
    ),
    type=click.IntRange(0, 4, clamp=True),
)
@click_help_colors.version_option(
    message=f"%(prog)s %(version)s (schema version {baseline.SCHEMA_VERSION})",
    message_color="bright_black",
    prog_name=baseline.__package__,
    prog_name_color="yellow",
    version=baseline.__version__,
    version_color="green",
)
@click.pass_context
def execute(
    context: click.core.Context,
    **options: typing.Dict[str, typing.Any],
) -> None:
    context.obj = options


def infer_filesystem_type(location: pathlib.Path) -> typing.Optional[str]:
    logger: logging.Logger = logging.getLogger(__name__)
    logger.debug("Infering filesystem type for location `%s`.", location)

    items: typing.List[typing.Tuple[str, str]] = list(
        map(operator.itemgetter(*(1, 2)), psutil.disk_partitions()),
    )
    items.sort(key=lambda item: len(pathlib.Path(item[0]).parts), reverse=True)

    for mountpoint, filesystem_type in items:
        if pathlib.Path(mountpoint) in location.parents:
            return filesystem_type

    return None


def validate_pairs(
    _context: click.core.Context,
    _parameter: click.core.Parameter,
    values: typing.List[str],
) -> typing.Dict[pathlib.Path, pathlib.Path]:
    associations: typing.Dict[pathlib.Path, pathlib.Path] = {}

    for pair in values:
        try:
            key, value = pair.split(":", 1)

        except ValueError:
            raise click.BadParameter("Pair must be 'key:value' (e.g. '/mnt/usb:/').")

        try:
            key: pathlib.Path = pathlib.Path(key).resolve(strict=True)

        except FileNotFoundError:
            raise click.BadParameter(f"Location `{key}` does not exist.")

        except PermissionError:
            raise click.BadParameter(
                f"Cannot resolve file `{key}` because of insufficient permissions.",
            )

        except RuntimeError:
            raise click.BadParameter(
                f"Probable infinite loop encountered while resolving entry `{key}`.",
            )

        except Exception:
            raise click.BadParameter(
                f"Unknown system exception raised while resolving entry {key}.",
            )

        try:
            associations[key] = pathlib.Path(value).resolve()

        except FileNotFoundError:
            raise click.BadParameter(f"Location `{value}` does not exist.")

        except PermissionError:
            raise click.BadParameter(
                f"Cannot open file `{value}` because of insufficient permissions.",
            )

        except RuntimeError:
            raise click.BadParameter(
                f"Probable infinite loop encountered while resolving entry `{value}`.",
            )

        except Exception:
            raise click.BadParameter(
                f"Unknown system exception raised while resolving entry {value}.",
            )

    return associations


class PlatformSpecificDefaults(click.Argument):
    def process_value(
        self,
        context: click.core.Context,
        value: str,
    ) -> click.Argument:
        return super().process_value(
            context,
            value or interface.PLATFORM_SPECIFIC_DEFAULTS["include"].get(platform.system(), []),
        )


class Renderer(abc.ABC):
    """Abstract base class that represents a renderer."""

    @property
    @abc.abstractclassmethod
    def TEMPLATE(cls: object) -> typing.Union[str, pathlib.Path]:
        """Class property that points the Jinja template to use."""

    def __init__(self: object) -> None:
        self.template = self.read_template()

    def read_template(self: object) -> jinja2.Template:
        """Reads Jinja template content."""

        return jinja2.Template(
            pathlib.Path(self.TEMPLATE).resolve().read_text(),
        )

    def render(
        self: object,
        **components: typing.Any,
    ) -> str:
        """Renders the templated file using the given components."""

        return self.template.render(**components)


class HtmlRenderer(Renderer):
    TEMPLATE = interface.ENVIRONMENT["root"] / "templates" / "html.jinja"


class NdjsonRenderer(Renderer):
    TEMPLATE = interface.ENVIRONMENT["root"] / "templates" / "ndjson.jinja"


@execute.command(
    cls=click_help_colors.HelpColorsCommand,
    context_settings={
        "max_content_width": 100,
    },
    help="Creates a new filesystem-based baseline.",
    help_headers_color="yellow",
    help_options_color="green",
    name="new",
    options_metavar="<options>",
)
@click.argument(
    "include",
    cls=PlatformSpecificDefaults,
    metavar="<path>...",
    nargs=-1,
    required=False,
    type=click.Path(
        exists=True,
        resolve_path=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "--comment",
    help="Add an arbitrary comment to the generated output file.",
    metavar="<str>",
)
@click.option(
    "--exclude-directory",
    default=interface.PLATFORM_SPECIFIC_DEFAULTS["exclude_directory"].get(platform.system(), []),
    help=(
        "Exclude a specific directory from the baseline. Can be specified "
        "multiple times (e.g. `--exclude-directory /dev --exclude-directory "
        "/proc`)."
    ),
    metavar="<directory>...",
    multiple=True,
    type=click.Path(
        file_okay=False,
        exists=True,
        resolve_path=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "--exclude-extractor",
    default=interface.PLATFORM_SPECIFIC_DEFAULTS["exclude_extractor"].get(platform.system(), []),
    help=(
        "Exclude extractors. Can be specified multiple times (e.g. `--exclude-extractor hash "
        "--exclude-extractor pe`)."
    ),
    multiple=True,
    type=click.Choice(
        {extractor.KEY for extractor in list(extractors.iterate_extractors())},
        case_sensitive=False,
    ),
    show_default=True,
)
@click.option(
    "--max-size",
    default=5000000,
    help="Set the maximum file size (in bytes) to inspect.",
    metavar="<int>",
    show_default=True,
    type=click.IntRange(1),
)
@click.option(
    "-o",
    "--output-file",
    help="Set the output file path (e.g. 'baseline.ndjson').",
    default=interface.PLATFORM_SPECIFIC_DEFAULTS["output_file"].get(platform.system()),
    metavar="<file>",
    show_default=True,
    type=click.Path(
        dir_okay=False,
        resolve_path=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "--output-file-encoding",
    default=interface.PLATFORM_SPECIFIC_DEFAULTS["output_file_encoding"].get(
        platform.system(),
        "utf-8",
    ),
    help="Set the output file encoding. Only applies when writing to an actual file.",
    show_default=True,
    type=click.Choice(
        interface.SUPPORTED_ENCODINGS,
        case_sensitive=False,
    ),
)
@click.option(
    "-f",
    "--output-format",
    default="ndjson",
    help="Set the output format.",
    show_default=True,
    type=click.Choice(
        ["html", "ndjson"],
        case_sensitive=False,
    ),
)
@click.option(
    "--partition-size",
    default=200,
    help="Set the partition size (i.e. number of entries per process).",
    metavar="<int>",
    show_default=True,
    type=click.IntRange(1),
)
@click.option(
    "--processes",
    default=os.cpu_count(),
    help="Set the number of parallel processes.",
    metavar="<int>",
    show_default=True,
    type=click.IntRange(1),
)
@click.option(
    "--recursive/--non-recursive",
    default=True,
    help=(
        "Whether to walk the filesystem recursively. When set, the program will only inspect the "
        "files and directories specifies on the first level of any included path. For example, if "
        "'/mnt/image' is specified as an included path, then only the directory '/mnt/image' "
        "itself and its direct children will be inspected."
    ),
    is_flag=True,
    show_default=True,
)
@click.option(
    "--remap",
    callback=validate_pairs,
    help=(
        "Artificially remap included paths (e.g. '/mnt/image:/'). Can be specified multiple times "
        "(e.g. `--remap /mnt/image:/ --remap /dev/null:/dev/void`)."
    ),
    metavar="<key:value>...",
    multiple=True,
    type=click.UNPROCESSED,
)
@click.option(
    "--report/--no-report",
    default=True,
    help="Whether to show a final report at the end.",
    is_flag=True,
    show_default=True,
)
@click.option(
    "--skip-compression",
    help="Whether to skip compression of the results.",
    is_flag=True,
)
@click.option(
    "--skip-directories",
    help="Whether to skip directories.",
    is_flag=True,
)
@click.option(
    "--skip-empty",
    help="Whether to skip empty entries.",
    is_flag=True,
)
@click.pass_context
def create_baseline(
    context: click.core.Context,
    comment,
    exclude_directory,
    exclude_extractor,
    include,
    max_size,
    recursive,
    output_file,
    output_file_encoding,
    output_format,
    partition_size,
    processes,
    skip_compression,
    skip_directories,
    skip_empty,
    remap,
    report,
) -> None:
    log_file: str = context.obj.get("log_file", f"{baseline.__package__}.log")
    monochrome: bool = context.obj.get("monochrome", False)
    verbose: int = context.obj.get("verbose", 0)

    # Monkey patch the logging time converter in order
    # to default to UTC instead of the local time.
    #
    logging.Formatter.converter = time.gmtime

    logger: logging.Logger = logging.getLogger(baseline.__name__)

    # Logging needs to be initialized at the very beginning
    # in order to display the earliest messages if needed.
    #
    if logging_configuration := context.obj.get("logging_configuration"):
        try:
            with logging_configuration.open() as stream:
                try:
                    configuration: typing.Dict[str, typing.Any] = json.load(stream)

                    logging.config.dictConfig(configuration)

                    logger.debug(
                        "Initialized logging using the configuration from file `%s`.",
                        logging_configuration,
                    )

                    if verbose > 0:
                        logger.warning(
                            "Verbosity overriden by the current logging configuration. The "
                            "`--verbose` flag is always ignored when using "
                            "`--logging-configuration`.",
                        )

                    if monochrome:
                        logger.warning(
                            "Monochromatism overriden by the current logging configuration. The "
                            "`--monochrome` flag is always ignored when using "
                            "`--logging-configuration`.",
                        )

                except json.JSONDecodeError as exception:
                    logger.exception(
                        "Failed to initialize the main logger using the configuration from `%s`.",
                        logging_configuration,
                    )

                    raise errors.Failure(
                        "failed to initialize logger using the configuration from "
                        f"`{logging_configuration}`",
                    ) from exception

        except PermissionError as exception:
            logger.warning(
                "Failed to read from file `%s` because of insufficient permissions.",
                logging_configuration,
            )

            raise errors.Failure(
                f"failed to read from `{logging_configuration}`",
            ) from exception

        except RuntimeError as exception:
            logger.error(
                "Probable infinite loop encountered while reading from file `%s`.",
                logging_configuration,
            )

            raise errors.Failure(
                f"failed to read from `{logging_configuration}`",
            ) from exception

        except Exception as exception:
            logger.exception(
                "Unknown system exception raised while reading from file `%s`.",
                logging_configuration,
            )

            raise errors.Failure(
                f"failed to read from `{logging_configuration}`",
            ) from exception

    else:
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)-24s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
        )

        if not monochrome and sys.__stdin__.isatty():
            console_handler: logging.Handler = rich.logging.RichHandler(
                level=logging.DEBUG,
                log_time_format="%Y-%m-%d %H:%M:%S",
                omit_repeated_times=False,
                rich_tracebacks=True,
            )

        else:
            console_handler: logging.Handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)

        file_handler: logging.FileHandler = logging.FileHandler(filename=log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        logger: logging.Logger = logging.getLogger(baseline.__package__)
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        # The logging level of the main logger is updated according to
        # the verbosity level the user asked for.
        #
        console_handler.setLevel(
            {
                0: logging.CRITICAL,
                1: logging.ERROR,
                2: logging.WARNING,
                3: logging.INFO,
                4: logging.DEBUG,
            }.get(verbose, logging.DEBUG),
        )

        logger.debug("Initialized logging using the built-in configuration.")

    logger: logging.Logger = logging.getLogger(__name__)

    # Log several system informations in order to improve later
    # debugging procedures.
    #
    logger.info("Included Locations        : %s", ", ".join(str(location) for location in include))
    logger.info(
        "Excluded Locations        : %s",
        ", ".join(str(location) for location in exclude_directory),
    )
    logger.info("Log File                  : %s", log_file)
    logger.info("Output File               : %s", output_file)
    logger.info("Output File Format        : %s", output_format)
    logger.info("Console Verbosity Level   : %d", verbose)
    logger.info(
        "File System Type          : %s",
        ", ".join(
            filter(
                functools.partial(operator.is_not, None),
                (infer_filesystem_type(location) for location in include),
            ),
        ),
    )
    logger.info("Program Version           : %s", baseline.__version__)
    logger.info("Operating System          : %s", platform.system())
    logger.info(
        "CPU Cores                 : %d (%d physical cores)",
        psutil.cpu_count(),
        psutil.cpu_count(logical=False),
    )
    logger.info(
        "Volatile Memory           : "
        f"{hfilesize.FileSize(psutil.virtual_memory().total):.01fH}",
    )

    disk_usage = psutil.disk_usage(output_file.parent)

    if disk_usage.free < 209715200:
        logger.warning(
            "Disk space is very low "
            f"({hfilesize.FileSize(disk_usage.free):.01fH}). Be aware that the "
            "resulting file can become quite big, depending on the number of "
            "entries that need to be processed.",
        )

    logger.info("Disk Usage                : %d%%", disk_usage.percent)
    logger.info("Language                  : %s", ".".join(locale.getdefaultlocale()))
    logger.info("System Timezone           : %s", datetime.datetime.now().astimezone().tzname())
    logger.info("Processor Architecture    : %s", platform.machine())
    logger.info("Computer Name             : %s", interface.ENVIRONMENT["node"])
    logger.info("Username                  : %s", getpass.getuser())
    logger.info("Effective User Identifier : %s", os.geteuid())
    logger.info("Effective Command Line    : %s", " ".join(sys.argv))
    logger.info(
        "Excluded Extractors       : %s",
        ", ".join(sorted(str(extractor) for extractor in exclude_extractor))
        if exclude_extractor
        else "",
    )
    logger.info("Current Working Directory : %s", interface.ENVIRONMENT["cwd"])

    start_time: datetime.datetime = datetime.datetime.utcnow()

    try:
        with core.Baseline(
            comment=comment,
            exclude_directory=exclude_directory,
            exclude_extractor=exclude_extractor,
            max_size=max_size,
            partition_size=partition_size,
            processes=processes,
            recursive=recursive,
            skip_compression=skip_compression,
            skip_directories=skip_directories,
            skip_empty=skip_empty,
            remap=remap,
        ) as executor:

            # The following is usually not a good pattern since we directly cast the returned
            # iterator into a list, loading all results into memory. Unfortunately, we need
            # this for Jinja templating to work as intended.
            results: typing.List[typing.Iterator[schema.Record]] = list(executor.compute(*include))

            count: int = len(results)

            try:
                renderer = {
                    "html": HtmlRenderer(),
                    "ndjson": NdjsonRenderer(),
                }

                components = {
                    "title": baseline.__package__.capitalize(),
                    "computer_name": interface.ENVIRONMENT["node"],
                    "records": results,
                }

                if skip_compression:
                    logger.warning(
                        "Skipping compression of the results because of the `--skip-compression` "
                        "flag. Be aware that the resulting file can become quite big, depending "
                        "on the number of entries that need to be processed.",
                    )
                    logger.debug("Writing the results to `%s`.", output_file)

                    with output_file.open(mode="w", encoding=output_file_encoding) as stream:
                        stream.write(renderer[output_format].render(**components))

                else:
                    output_file: pathlib.Path = output_file.with_suffix(f"{output_file.suffix}.xz")

                    logger.debug("Compressing and writing the results to `%s`.", output_file)

                    with lzma.open(output_file, mode="wb") as stream:
                        stream.write(
                            renderer[output_format]
                            .render(**components)
                            .encode(output_file_encoding)
                        )

            except PermissionError:
                logger.error(
                    "Failed to open file `%s` for writing because of insufficient " "permissions.",
                    output_file,
                )

                sys.exit(os.EX_SOFTWARE)

            except RuntimeError:
                logger.error(
                    "Probable infinite loop encountered while opening file `%s` for writing.",
                    output_file,
                )

                sys.exit(os.EX_SOFTWARE)

            except Exception:
                logger.exception(
                    "Unknown system exception raised while opening file `%s` for writing.",
                    output_file,
                )

                sys.exit(os.EX_SOFTWARE)

            duration: datetime.timedelta = datetime.datetime.utcnow() - start_time

            total_size = output_file.stat().st_size

            logger.info("Written `%d` bytes of results to `%s`.", total_size, output_file)
            logger.info("Finished in `%s`.", duration)

            if report:
                rich.print("[bold green]All done![/bold green] :muscle:\n")
                rich.print(f"Entries Processed : {count}")
                rich.print(f"Output Format     : {output_format}")
                rich.print(f"Output File       : {output_file}")
                rich.print(f"Size              : {hfilesize.FileSize(total_size):.01fH}")
                rich.print(f"Total Time        : {duration}")

    except KeyboardInterrupt:
        logger.warning(
            "Process pool shut down. Exiting now after `%s`.",
            datetime.datetime.utcnow() - start_time,
        )

        sys.exit(os.EX_SOFTWARE)

    except errors.ValidationError as exception:
        logger.error(
            "Validation error in the `%s.core.%s` class attributes `%s`.",
            baseline.__package__,
            core.Baseline.__name__,
            ", ".join(exception.parameters),
        )

        sys.exit(os.EX_SOFTWARE)

    except errors.Failure:
        logger.exception(
            "Unrecoverable failure occurred. Exiting now after `%s`.",
            datetime.datetime.utcnow() - start_time,
        )

        raise


@execute.command(
    cls=click_help_colors.HelpColorsCommand,
    context_settings={
        "max_content_width": 100,
    },
    help="Show the JSON representation of the actual schema.",
    help_headers_color="yellow",
    help_options_color="green",
    name="schema",
    options_metavar="<options>",
)
@click.option(
    "--compact",
    help="Render compact JSON instead of the default idented version.",
    is_flag=True,
)
@click.option(
    "--output-file",
    help="Set the output file path (e.g. 'schema.json').",
    metavar="<file>",
    type=click.Path(
        dir_okay=False,
        writable=True,
        readable=False,
        resolve_path=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    "--output-file-encoding",
    default=interface.PLATFORM_SPECIFIC_DEFAULTS["output_file_encoding"].get(
        platform.system(),
        "utf-8",
    ),
    help="Set the output file encoding. Only applies when writing to an actual file.",
    show_default=True,
    type=click.Choice(
        interface.SUPPORTED_ENCODINGS,
        case_sensitive=False,
    ),
)
@click.pass_context
def print_schema(
    context: click.core.Context,
    output_file,
    output_file_encoding,
    compact,
) -> None:

    logger: logging.Logger = logging.getLogger(__name__)

    output: str = json.dumps(
        pydantic.schema.model_schema(schema.Record),
        indent=2 if not compact else None,
    )

    if output_file:
        try:
            with output_file.open("w", encoding=output_file_encoding) as stream:
                stream.write(output + "\n")

        except PermissionError as exception:
            logger.error(
                "Failed to open file `%s` for writing because of insufficient permissions.",
                output_file,
            )

            raise errors.Failure(
                f"cannot open file `{output_file}` because of insufficient permissions",
            ) from exception

        except RuntimeError as exception:
            logger.error(
                "Probable infinite loop encountered while opening file `%s` for writing.",
                output_file,
            )

            raise errors.Failure(f"failed to open file `{output_file}`") from exception

        except Exception as exception:
            logger.exception(
                "Unknown system exception raised while opening file `%s` for writing.",
                output_file,
            )

            raise errors.Failure(f"failed to open file `{output_file}`") from exception

    elif context.obj.get("monochrome", False):
        sys.stdout.write(output + "\n")

    else:
        rich.print_json(output, indent=2 if not compact else None)
