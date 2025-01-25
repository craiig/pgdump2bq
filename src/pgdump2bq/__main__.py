import argparse
import logging
import os
import sys

from .dump_all_tables import dump_all_tables
from .fix_table_schema import convert_hstore_to_jsonb, fix_all_yaml_columns
from .postgres import pg_restore, run_sql_file, temp_postgresql_db

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure python logging to emit to stdout."""

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        # display isoformat time, log level, module, line number, message
        format="%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Fixes a pgdump file for import")
    parser.add_argument(
        "--sql-before-import", help="The file to execute before the pgdump is imported"
    )
    parser.add_argument("--pgdump", help="The pgdump file to import", required=True)
    parser.add_argument(
        "--output-directory",
        help="The directory to write the output files",
        required=True,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Keep running to enable debugging by connecting to the postgresql database",
    )
    args = parser.parse_args()

    assert os.path.exists(args.output_directory), "output directory should be created"

    # initialize postgresql in temp folder
    # create database in temp folder for duration of run
    with temp_postgresql_db("."):
        try:
            if args.sql_before_import:
                run_sql_file(args.sql_before_import)

            pg_restore(args.pgdump)

            try:
                convert_hstore_to_jsonb()
            except Exception:
                logger.exception("something went wrong while fixing schemas")
                raise

            try:
                fix_all_yaml_columns("activity_datas", "content")
            except Exception:
                logger.exception(
                    "something went wrong while converting yaml to json column"
                )
                raise

            # resolve path to absolute
            dump_all_tables(os.path.abspath(args.output_directory))
            logger.info("Done export")
        finally:
            if args.debug:
                logger.info(
                    "Waiting in debug mode, press CTRL+D or CTRL+C to close postgresql and exit"
                )
                while True:
                    l = sys.stdin.readline()
                    if not l:
                        break


if __name__ == "__main__":
    main()
