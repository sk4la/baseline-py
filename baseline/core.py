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

import concurrent.futures
import concurrent.futures.process
import logging
import logging.config
import operator
import os
import pathlib
import signal
import sys
import types
import typing
import warnings

import magic
import pydantic

from baseline import errors, extractors, models, schema

__all__: typing.Tuple[str, ...] = ("Baseline",)


def teardown_worker(sig: int, _: typing.Optional[typing.Any] = None) -> None:
    logger: logging.Logger = logging.getLogger(__name__)
    logger.critical(
        "Catched signal `%s` inside the current process (pid `%d`). Exiting now.",
        signal.Signals(sig).name or str(sig),
        os.getpid(),
    )

    sys.exit(os.EX_SOFTWARE)


def initialize_worker() -> None:
    signal.signal(signal.SIGINT, teardown_worker)


def gather_filesystem_entries(
    root: pathlib.Path,
    exclude_directory: typing.List[pathlib.Path] = [],
    max_size: typing.Optional[int] = None,
    recursive: bool = True,
    skip_directories: bool = False,
    skip_empty: bool = False,
) -> typing.Tuple[pathlib.Path, typing.List[typing.Tuple[pathlib.Path, int]]]:
    logger: logging.Logger = logging.getLogger(__name__)

    logger.debug(
        "Gathering files %sfrom root location `%s`.",
        "recursively " if recursive else "",
        root,
    )

    results: typing.List[typing.Tuple[pathlib.Path, int]] = []

    try:
        for entry in root.glob("*") if not recursive else root.rglob("*"):
            for directory in exclude_directory:
                if directory in entry.parents:
                    logger.debug(
                        "Ignoring entry `%s` from excluded directory `%s`.", entry, directory
                    )

                    continue

            if entry.is_file():
                kind: int = models.kinds.FILE

            elif entry.is_dir():
                if skip_directories:
                    logger.debug(
                        "Skipping directory `%s` because of the `--skip-directories` flag.",
                        entry,
                    )

                    continue

                kind: int = models.kinds.DIRECTORY

            elif entry.is_block_device():
                kind: int = models.kinds.BLOCK_DEVICE

            elif entry.is_char_device():
                kind: int = models.kinds.CHARACTER_DEVICE

            elif entry.is_fifo():
                kind: int = models.kinds.FIFO

            elif entry.is_socket():
                kind: int = models.kinds.SOCKET

            elif entry.is_symlink():
                kind: int = models.kinds.SYMLINK

            elif entry.is_mount():
                kind: int = models.kinds.MOUNT

            else:
                kind: int = models.kinds.OTHER

            try:
                stats = entry.stat(follow_symlinks=kind != models.kinds.SYMLINK)

            except TypeError:
                if sys.version_info >= (3, 10):
                    raise

                warnings.warn(
                    "The `follow_symlinks` parameter was only added to `pathlib.Path.stat` in Python "
                    "3.10 so it cannot be used with the current installation of Python ("
                    f"{'.'.join(str(_) for _ in sys.version_info[:3])}). Update your installation to "
                    "remove this warning. Falling back to the old way (following all symlinks)."
                )

                try:
                    stats = entry.stat()

                except PermissionError:
                    logger.warning(
                        "Failed to access entry `%s` because of insufficient permissions. Skipping.",
                        entry,
                    )

                    continue

                except FileNotFoundError:
                    logger.error(
                        "Cannot access entry `%s` since it does not exist. This can be caused by "
                        "temporary files that have been unlinked before reaching processing. Skipping.",
                        entry,
                    )

                    continue

                except RuntimeError:
                    logger.error(
                        "Probable infinite loop encountered while accessing entry `%s`. Skipping.",
                        entry,
                    )

                    continue

                except Exception:
                    logger.exception(
                        "Unknown system exception raised while accessing entry `%s`. Skipping.",
                        entry,
                    )

                    continue

            if skip_empty and not stats.st_size:
                logger.debug(
                    "Skipping empty entry `%s` because of the `--skip-empty` flag.", entry
                )

                continue

            if max_size and (stats.st_size > max_size):
                logger.debug(
                    "Skipping entry `%s` because it exceeds the maximum threshold of `%d` "
                    "bytes. You can override this threshold using the `--max-size` option.",
                    entry,
                    max_size,
                )

                continue

            results.append((entry, kind))

    except PermissionError:
        logger.warning(
            "Failed to access an entry under root location `%s` because of "
            "insufficient permissions. This is usually caused by ephemeral "
            "directories, there are no easy fixes at the moment. Cannot continue "
            "gathering entries from this location. Skipping.",
            root,
        )

    except FileNotFoundError:
        logger.error(
            "Failed to access a nonexistent entry under root location `%s`. "
            "This is usually caused by ephemeral directories, there are no easy fixes "
            "at the moment. Cannot continue gathering entries from this location. "
            "Skipping.",
            root,
        )

    except RuntimeError:
        logger.error(
            "Probable infinite loop encountered while recursing through entries "
            "under root location `%s`. Cannot continue gathering entries "
            "from this location. Skipping.",
            root,
        )

    except Exception:
        logger.exception(
            "Unknown system exception raised while recursing through entries "
            "under root location `%s`. Cannot continue gathering entries "
            "from this location. Skipping.",
            root,
        )

    return (root, results)


def process_partition(
    partition: typing.List[typing.Tuple[pathlib.Path, int]],
    exclude_extractor: typing.List[str],
    remap: typing.Dict[pathlib.Path, pathlib.Path],
    magic_bytes_lookahead: int = 1024,
) -> typing.List[schema.Record]:
    logger: logging.Logger = logging.getLogger(__name__)
    logger.debug("Analyzing `%d` entries.", len(partition))

    records: typing.List[schema.Record] = []

    for entry, kind in partition:
        magic_signature: typing.Optional[str] = None
        mime_type: typing.Optional[str] = None

        if kind in (
            models.kinds.FILE,
            models.kinds.BLOCK_DEVICE,
        ):
            try:
                with entry.open("rb") as stream:
                    header: bytes = stream.read(magic_bytes_lookahead)

                    magic_signature = magic.from_buffer(header)
                    mime_type = magic.from_buffer(header, mime=True)

            except PermissionError:
                logger.error(
                    "Failed to open file `%s` because of insufficient permissions. Skipping.",
                    entry,
                )

                continue

            except FileNotFoundError:
                logger.error(
                    "Cannot open entry `%s` since it does not exist. This can be caused by "
                    "temporary files that have been unlinked before reaching processing. "
                    "Skipping.",
                    entry,
                )

                continue

            except RuntimeError:
                logger.error(
                    "Probable infinite loop encountered while opening entry `%s`. Skipping.",
                    entry,
                )

                continue

            except Exception:
                logger.exception(
                    "Unknown system exception raised while opening entry `%s`. Skipping.",
                    entry,
                )

                continue

        record: schema.Record = schema.Record(
            signature=schema.Signature(
                kind=models.kinds.humanize(kind),
                magic=magic_signature,
                mime=mime_type,
            ),
        )

        for extractor in extractors.iterate_extractors(exclude=exclude_extractor):
            if extractor.supports(entry, kind=kind, magic_signature=magic_signature):
                try:
                    module: models.Extractor = extractor(entry, remap=remap)
                    module.run(record)

                    logger.debug("Merged output from extractor `%s`.", extractor.KEY)

                except errors.GenericError:
                    logger.error(
                        "Failed to extract information from entry `%s` (%s) because of an "
                        "exception in extractor `%s`.",
                        entry,
                        models.kinds.humanize(kind),
                        extractor.KEY,
                    )

                except Exception:
                    logger.exception(
                        "Failed to extract information from entry `%s` (%s) because of an "
                        "unrecoverable exception in extractor `%s`.",
                        entry,
                        models.kinds.humanize(kind),
                        extractor.KEY,
                    )

        records.append(record)

    return records


class BaselineAttributes(pydantic.BaseModel):
    comment: typing.Optional[str]
    exclude_directory: typing.List[pydantic.DirectoryPath]
    exclude_extractor: typing.List[str]
    include: typing.List[pathlib.Path] = []
    max_size: int
    partition_size: int
    processes: int = os.cpu_count() or 1
    recursive: bool
    remap: typing.Dict[pydantic.DirectoryPath, pathlib.Path]
    skip_compression: bool
    skip_directories: bool
    skip_empty: bool

    class Config:
        allow_mutation = False


class Baseline:
    def __init__(
        self: object,
        comment: typing.Optional[str] = None,
        exclude_directory: typing.List[typing.Union[str, pathlib.Path]] = [],
        exclude_extractor: typing.List[str] = [],
        max_size: int = 5000000,
        partition_size: int = 200,
        processes: int = os.cpu_count() or 1,
        recursive: bool = True,
        remap: typing.Dict[typing.Union[str, pathlib.Path], typing.Union[str, pathlib.Path]] = {},
        skip_compression: bool = False,
        skip_directories: bool = False,
        skip_empty: bool = False,
    ) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)

        # Prevent the firing of a warning when no logging handler has been set.
        self.logger.addHandler(logging.NullHandler())

        try:
            self.parameters: BaselineAttributes = BaselineAttributes(
                comment=comment,
                exclude_directory=[
                    pathlib.Path(location).resolve(strict=True) for location in exclude_directory
                ],
                exclude_extractor=exclude_extractor,
                max_size=max_size,
                partition_size=partition_size,
                processes=processes,
                recursive=recursive,
                remap={
                    pathlib.Path(source).resolve(strict=True): pathlib.Path(destination).resolve()
                    for source, destination in remap.items()
                },
                skip_compression=skip_compression,
                skip_directories=skip_directories,
                skip_empty=skip_empty,
            )

        except FileNotFoundError as exception:
            raise errors.GenericError(f"entry `{exception.filename}` not found") from exception

        except pydantic.ValidationError as exception:
            outliers: typing.List[str] = list(
                map(operator.itemgetter(0), (map(operator.itemgetter("loc"), exception.errors()))),
            )

            self.logger.exception(
                "Validation error in the `%s` class attributes `%s`.",
                __name__,
                ", ".join(outliers),
            )

            raise errors.ValidationError(
                "validation error in class attributes",
                context={
                    "parameters": outliers,
                },
            ) from exception

        try:
            self.pool: concurrent.futures.ProcessPoolExecutor = (
                concurrent.futures.ProcessPoolExecutor(
                    initializer=initialize_worker,
                    max_workers=self.parameters.processes,
                )
            )

            self.logger.debug(
                "Initialized pool of `%d` worker processes.",
                self.parameters.processes,
            )

        except concurrent.futures.process.BrokenProcessPool as exception:
            self.logger.exception(
                "Unrecoverable failure in multiprocessing pool. Exiting now.",
            )

            raise errors.GenericError("process pool shut down abruptly") from exception

        self.futures: typing.Dict[str, typing.Set[concurrent.futures.Future]] = {
            "gathering": set(),
            "analysis": set(),
        }

    def __split_partitions(
        self: object,
        items: typing.List[typing.Any],
        count: int = 1,
    ) -> typing.Iterator[typing.List[typing.Any]]:

        for index in range(0, len(items), count):
            yield items[index : index + count]

    def __enter__(self: object) -> object:
        return self

    def __exit__(
        self: object,
        kind: typing.Any,
        value: typing.Optional[Exception],
        traceback: typing.Optional[types.TracebackType],
    ) -> None:
        # Dispatching to the right handler, depending on the exception that has
        # been raised. If none can be identified, then we panic (raise a generic
        # exception with the complete traceback).
        #
        if traceback:
            {KeyboardInterrupt: self.__interrupt}.get(
                kind,
                self.__panic,
            )(kind, value, traceback)

        self.pool.shutdown()

        # Manually close the ProcessPoolExecutor context manager that we opened
        # in the constructor.
        #
        self.pool.__exit__(None, None, None)

    def __panic(
        self: object,
        _: typing.Optional[typing.Any],
        value: typing.Optional[BaseException],
        traceback: typing.Optional[types.TracebackType],
    ) -> None:
        if traceback:
            self.logger.exception("Fatal exception caught.")

            self.pool.shutdown()

            raise errors.GenericError("process pool shut down abruptly") from value

    def __interrupt(
        self: object,
        *_args: typing.Any,
        **_kwargs: typing.Any,
    ) -> None:
        self.logger.critical("Interrupted by manual user action. Cancelling the current tasks.")

        for group in self.futures.values():
            for future in group:
                future.cancel()

        self.logger.info("Waiting for the ongoing tasks to finish properly.")

        self.pool.shutdown()

        raise KeyboardInterrupt

    def compute(
        self: object,
        *include: pathlib.Path,
        exclude_directory: typing.Optional[typing.List[pathlib.Path]] = None,
        exclude_extractor: typing.Optional[typing.List[str]] = None,
        max_size: typing.Optional[int] = None,
        partition_size: typing.Optional[int] = None,
        recursive: typing.Optional[bool] = None,
        remap: typing.Optional[typing.Dict[pathlib.Path, pathlib.Path]] = None,
        skip_compression: typing.Optional[bool] = None,
        skip_directories: typing.Optional[bool] = None,
        skip_empty: typing.Optional[bool] = None,
        comment: typing.Optional[str] = None,
    ) -> typing.Iterator[schema.Record]:

        try:
            if exclude_directory is not None:
                exclude_directory = [
                    pathlib.Path(location).resolve(strict=True) for location in exclude_directory
                ]

            if remap is not None:
                remap = {
                    pathlib.Path(source).resolve(strict=True): pathlib.Path(destination).resolve()
                    for source, destination in remap.items()
                }

            # Any parameter given to the current method will override the one set at class
            # initialization.
            parameters: BaselineAttributes = BaselineAttributes(
                comment=comment or self.parameters.comment,
                exclude_directory=exclude_directory or self.parameters.exclude_directory,
                exclude_extractor=exclude_extractor or self.parameters.exclude_extractor,
                include=[pathlib.Path(location).resolve(strict=True) for location in include],
                max_size=max_size or self.parameters.max_size,
                partition_size=partition_size or self.parameters.partition_size,
                recursive=recursive or self.parameters.recursive,
                remap=remap or self.parameters.remap,
                skip_compression=skip_compression or self.parameters.skip_compression,
                skip_directories=skip_directories or self.parameters.skip_directories,
                skip_empty=skip_empty or self.parameters.skip_empty,
            )

        except FileNotFoundError as exception:
            raise errors.GenericError(f"entry `{exception.filename}` not found") from exception

        except pydantic.ValidationError as exception:
            outliers: typing.List[str] = list(
                map(operator.itemgetter(0), (map(operator.itemgetter("loc"), exception.errors()))),
            )

            self.logger.exception(
                "Validation error in the `%s` class attributes `%s`.",
                __name__,
                ", ".join(outliers),
            )

            raise errors.ValidationError(
                "validation error in class attributes",
                context={
                    "parameters": outliers,
                },
            ) from exception

        with self.pool as executor:
            for root in parameters.include:
                self.futures["gathering"].add(
                    executor.submit(
                        gather_filesystem_entries,
                        root,
                        exclude_directory=parameters.exclude_directory,
                        max_size=parameters.max_size,
                        recursive=parameters.recursive,
                        skip_directories=parameters.skip_directories,
                        skip_empty=parameters.skip_empty,
                    ),
                )

            self.logger.info(
                "Gathering entries from a total of `%d` root locations.",
                len(parameters.include),
            )

            for future in concurrent.futures.as_completed(self.futures["gathering"]):
                root, entries = future.result()

                self.futures["gathering"].remove(future)

                total: int = len(entries)

                if not total:
                    self.logger.info(
                        "No entries gathered from root location `%s`. " "Skipping.",
                        root,
                    )

                    continue

                self.logger.info(
                    "Partitioning a total of `%d` entries from root location "
                    "`%s` with a rate of `%d` entries per process (ratio `%.1f`).",
                    total,
                    root,
                    parameters.partition_size,
                    float(total) / float(parameters.partition_size),
                )

                for partition in self.__split_partitions(entries, parameters.partition_size):
                    self.futures["analysis"].add(
                        executor.submit(
                            process_partition,
                            partition,
                            exclude_extractor=parameters.exclude_extractor,
                            remap=parameters.remap,
                        ),
                    )

                for future in concurrent.futures.as_completed(self.futures["analysis"]):
                    records = future.result()

                    self.futures["analysis"].remove(future)

                    total: int = len(records)

                    if not records:
                        self.logger.info(
                            "No records to yield. Skipping.",
                        )

                        continue

                    self.logger.debug(
                        "Yielding `%d` records from future `%d`.",
                        total,
                        hash(future),
                    )

                    for record in records:
                        record.comment = parameters.comment

                        yield record
