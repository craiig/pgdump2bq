import contextlib
import logging
import signal
import tempfile

import psycopg2
from retry import retry

from .subprocess_helper import run_command, run_command_async

logger = logging.getLogger(__name__)


server_port = 1234
target_database_name = "dump_import"


# We decorate this function with retry since the postgresql database may not be initialized
@retry(logger=logger, delay=1)
def connect_database(dbname=target_database_name):
    return psycopg2.connect(
        host="localhost",
        port=server_port,
        dbname=dbname,
    )


def run_sql_file(filename: str):
    logger.info(f"running {filename}")
    run_command(
        f"psql -h localhost -p {server_port} -d {target_database_name} -f {filename} -v ON_ERROR_STOP=on"
    )


def pg_restore(dump_file: str):
    run_command("pg_restore --version")
    run_command(
        f"pg_restore -v -c -O --if-exists -d {target_database_name} -h localhost "
        f"-p {server_port} {dump_file}"
    )


def create_database():
    """
    run SELECT 1 on postgresql database using psycopg2
    """
    logger.info("creating database")
    conn = connect_database(dbname="postgres")
    conn.set_session(autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"create database {target_database_name}")


@contextlib.contextmanager
def temp_postgresql_db(path: str):
    server_process = None
    try:
        with tempfile.TemporaryDirectory("pgimport", dir=path) as tempdir:
            logger.info("initializing postgresql")
            run_command(f"initdb -d {tempdir}")

            logger.info("starting postgresql")
            server_process = run_command_async(
                f"postgres -D {tempdir} -p {server_port}"
            )

            create_database()

            logger.info("postgresql ready")
            yield
    finally:
        if server_process is not None:
            logger.info("Terminating postgresql")
            server_process.send_signal(signal.SIGINT)
