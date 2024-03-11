import argparse
import logging
import os
import sys

from .dump_all_tables import dump_all_tables
from .fix_table_schema import convert_hstore_to_jsonb
from .postgres import pg_restore, run_sql_file, temp_postgresql_db

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure python logging to emit to stdout."""

    logging.basicConfig(
        level=logging.INFO,
        # improve formatting
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
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
        if args.sql_before_import:
            run_sql_file(args.sql_before_import)

        pg_restore(args.pgdump)

        try:
            convert_hstore_to_jsonb()
        except Exception:
            logger.exception("something went wrong while fixing schemas")

        # resolve path to absolute
        dump_all_tables(os.path.abspath(args.output_directory))

    logger.info("Done export")
    if args.debug:
        logger.info("Press CTRL+D or CTRL+C to close postgresql and exit")
        while True:
            l = sys.stdin.readline()
            if not l:
                break


if __name__ == "__main__":
    setup_logging()
    main()
