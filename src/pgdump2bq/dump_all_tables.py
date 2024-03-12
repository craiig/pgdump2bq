import logging

from .postgres import connect_database
from .subprocess_helper import run_command

logger = logging.getLogger(__name__)


def dump_all_tables(output_directory: str):
    """
    Dumps all tables in the current database to the output directory in parquet format.

    We use ogr2ogr because it has a built-in parquet format that supports geometry that BigQuery supposedly handles well.
    """
    conn = connect_database()
    with conn.cursor() as cur:
        cur.execute(
            """
                SELECT (table_schema || '.' || table_name) AS schema_table
                FROM information_schema.tables t INNER JOIN information_schema.schemata s 
                ON s.schema_name = t.table_schema 
                WHERE 
                t.table_schema NOT IN ('pg_catalog', 'information_schema', 'configuration')
                AND t.table_type NOT IN ('VIEW')
                ORDER BY schema_table;
            """
        )

        logger.info("dumping tables")

        for row in cur.fetchall():
            table = row[0]
            destination = f"{output_directory}/{table}.parquet"
            run_command(
                f'ogr2ogr -f Parquet "{destination}" PG:"host=localhost port=1234 dbname=dump_import" -sql "select * from {table}"'
            )
            logger.info(f"dumped {table} to {destination}")
