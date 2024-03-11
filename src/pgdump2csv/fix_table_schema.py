import logging

from .postgres import connect_database

logger = logging.getLogger(__name__)


def convert_hstore_to_jsonb():
    """
    Find all columns in the database with type hstore, and convert them to jsonb.

    The idea here is that JSON strings are better handled by bigquery than hstore strings.
    """
    conn = connect_database()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_schema, table_name, column_name
            FROM information_schema.columns
            WHERE 
            table_schema NOT IN ('pg_catalog', 'information_schema', 'configuration')
            AND udt_name = 'hstore';
            """
        )

        for row in cur.fetchall():
            table_schema, table_name, column_name = row
            logger.info(
                f"converting column {column_name} in table {table_name} from hstore to jsonb"
            )
            query = f"""
                ALTER TABLE "{table_schema}"."{table_name}" ALTER COLUMN {column_name} TYPE jsonb USING shared_extensions.hstore_to_jsonb({column_name});
                """
            logger.debug(query)
            cur.execute(query)
            logger.info(f"done converting {table_schema}.{table_name}")

    conn.commit()
    conn.close()
