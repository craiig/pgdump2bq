# pgdump2bq

This tool converts a PostgreSQL dump file to a series of files that are suitable for import into Google BigQuery.

There are several other tools designed for exporting PostgreSQL to a given format, but this tool differs from them in a few key ways:
1. This tool creates a temporary PostgreSQL database from a pgdump file and then extracts the data. This differs from 
   other tools which require you to perform this step manually into an existing PostgreSQL database.
2. Instead of targetting a specific format, this tool is optimized to generate files specifically for importing into BigQuery.

These are notable because:
* #1 means we can to modify tables/columns inside PostgreSQL before exporting, taking advantage of PostgreSQL's own tools/performance. 
* #2 means the output format of this tool may change over time. Currently it outputs Parquet, but as BigQuery evolves, this tool can too.

For instance, `hstore` type fields are converted to `json` before export. More such conversion may be done in the future.

This tool is written in python, but it avoids being on the datapath of most operations. It calls out to PostgreSQL and gdal/ogr2ogr to import and export.

## Installing
Requirements:
* A PostgreSQL installation on the path. Including `initdb`, `postgres`, and `psql`.
* GDAL 3.8.4 (for `ogr2ogr`)
* Rye - https://rye-up.com/

```
git clone ...
rye sync
```

## Basic Usage

```
usage: main.py [-h] [--sql-before-import SQL_BEFORE_IMPORT] --pgdump PGDUMP --output-directory OUTPUT_DIRECTORY [--debug]

Fixes a pgdump file for import

options:
  -h, --help            show this help message and exit
  --sql-before-import SQL_BEFORE_IMPORT
                        The file to execute before the pgdump is imported
  --pgdump PGDUMP       The pgdump file to import
  --output-directory OUTPUT_DIRECTORY
                        The directory to write the output files
  --debug               Keep running to enable debugging by connecting to the PostgreSQL database
```

Example:
```
% python -m pgdump2bq --sql-before-import config.sql --pgdump file.pgdump --output-directory testoutput
```


## Development: 

This project was created with rye - https://rye-up.com/

Check out this repo, and run `rye sync` to initialze the virtualenv.

Consider the code in this repo to be hobbyist level, at best. :) 


# Manual Instructions
Basic manual instructions for loading postgres dump and create the best possible export for import into bigquery
This tool was developed to solve a specific problem, the manual steps to perform the same operations are described here for posterity.


### 1. Install PostgreSQL with PostGIS extensions
TODO find good link, this is beyond the scope of these instructions

If you're on MacOS, try homebrew.

### 2. Create database
1. Create database in test directory: `initdb -d test`
1. Run PostgreSQL server on port 1234: `postgres -D test -p 1234`
1. Connect to database `psql -h localhost -p 1234 -d postgres`
1. Create the database to import into: `create database dump_import;`


### 3. Configure dump-specific prerequisities:

#### For NationBuilder
This is focused on importing NationBuilder dumps.

We need to configure `shared_extensions` like the NationBuilder dump expects:
Connect to new database `psql -h localhost -p 1234 -d dump_import`

More details:
https://support.nationbuilder.com/en/articles/2362780-how-to-backup-your-nation#restoring-your-nation

```
CREATE SCHEMA if not exists shared_extensions;
CREATE EXTENSION if not exists hstore WITH schema shared_extensions; 
CREATE EXTENSION if not exists dblink WITH schema shared_extensions; 
CREATE EXTENSION if not exists citext WITH schema shared_extensions; 
CREATE EXTENSION if not exists pg_trgm WITH schema shared_extensions;
CREATE EXTENSION if not exists postgis with schema shared_extensions;
```

### 4. Import Dump
```
pg_restore -v -c -O --if-exists -d dump_import -h localhost -p 1234 path/to/dumpfile
```

#### Modify hstore columns in dump to json
hstore is not a format that BigQuery supports, so it is better to turn these fields into json.
```
alter table schema.table alter column custom_values type jsonb using shared_extensions.hstore_to_jsonb(custom_values);
```

### 5. Export to Parquet
```
ogr2ogr -f Parquet test.parquet PG:"host=localhost port=1234 dbname=dump_import" -sql "select * from schema.table"
```

### 5. Alternate: Turn all tables into CSV files

Caveat - this works but it does not preserve the field types - so importing 
this into another databse may be tricky.

1. Determine your destination path:
```
mkdir output
cd output
cwd
```

1. Install pl/pgsql function taken from here: https://stackoverflow.com/a/37210706

Run: `psql -h localhost -p 1234 -d dump_import`
```
CREATE OR REPLACE FUNCTION db_to_csv(path TEXT) RETURNS void AS $$
declare
   tables RECORD;
   statement TEXT;
begin
FOR tables IN 
   SELECT (table_schema || '.' || table_name) AS schema_table
   FROM information_schema.tables t INNER JOIN information_schema.schemata s 
   ON s.schema_name = t.table_schema 
   WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema', 'configuration')
   AND t.table_type NOT IN ('VIEW')
   ORDER BY schema_table
LOOP
   statement := 'COPY ' || tables.schema_table || ' TO ''' || path || '/' || tables.schema_table || '.csv' ||''' DELIMITER '';'' CSV HEADER';
   EXECUTE statement;
END LOOP;
return;  
end;
$$ LANGUAGE plpgsql;
```

1. Execute: `SELECT db_to_csv('/absolute/destination/path');`

1. All the dumped files should be in the expected spot!
