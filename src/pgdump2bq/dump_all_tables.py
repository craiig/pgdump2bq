import asyncio
import logging

from .postgres import connect_database
from .subprocess_helper import run_command_async_await

logger = logging.getLogger(__name__)


async def dump_all_tables(output_directory: str, max_concurrent_dumps: int = 100):
    """
    Dumps all tables in the current database to the output directory in parquet format.

    We use ogr2ogr because it has a built-in parquet format that supports geometry that BigQuery supposedly handles well.
    
    Args:
        output_directory: Directory to write parquet files
        max_concurrent_dumps: Maximum number of concurrent table dumps (default: 5)
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

        # Get all table names first
        tables = [row[0] for row in cur.fetchall()]

    # Create semaphore to limit concurrent dumps
    semaphore = asyncio.Semaphore(max_concurrent_dumps)

    # Create async tasks for all table dumps
    async def dump_table(table: str):
        async with semaphore:  # Limit concurrent operations
            destination = f"{output_directory}/{table}.parquet"
            await run_command_async_await(
                f'ogr2ogr -f Parquet "{destination}" PG:"host=localhost port=1234 dbname=dump_import" -sql "select * from {table}"'
            )
            logger.info(f"dumped {table} to {destination}")

    # Run all dumps concurrently with the semaphore limit
    logger.info(f"Starting concurrent dump of {len(tables)} tables (max {max_concurrent_dumps} concurrent)")
    tasks = [dump_table(table) for table in tables]
    await asyncio.gather(*tasks)
    logger.info(f"Completed dumping all {len(tables)} tables")
