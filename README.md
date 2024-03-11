
# Basic instructions for loading postgres dump and create the best possible export for import into bigquery

## 1. Install Postgresql with PostGIS extensions
TODO find good link, this is beyond the scope of these instructions

If you're on MacOS, try homebrew.

## 2. Create database
1. Create database in test directory: `initdb -d test`
1. Run postgresql server on port 1234: `postgres -D test -p 1234`
1. Connect to database `psql -h localhost -p 1234 -d postgres`
1. Create the database to import into: `create database dump_import;`


## 3. Configure dump-specific prerequisities:

### For NationBuilder
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

## 4. Import Dump
```
pg_restore -v -c -O --if-exists -d dump_import -h localhost -p 1234 path/to/dumpfile
```

### Maybe - Modify hstore columns in dump to json
```
alter table nbuild_onecity.signups alter column custom_values type jsonb using shared_extensions.hstore_to_jsonb(custom_values);
```

## 5. Turn all tables into CSV files

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

## Export to Parquet
```
ogr2ogr -f Parquet test.parquet PG:"host=localhost port=1234 dbname=dump_import" -sql "select * from nbuild_onecity.signups"
```

# Future work
* Turn this into a program/script.
	* Given a pg_dump file with name PGDUMPFILE
	* Creates CSV in directory structure: PGDUMPFILE/schema/table.csv

* Investigate file formats for output that would preserve types, i.e. parquet
