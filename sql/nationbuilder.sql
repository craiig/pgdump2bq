CREATE SCHEMA if not exists shared_extensions;
CREATE EXTENSION if not exists hstore WITH schema shared_extensions; 
CREATE EXTENSION if not exists dblink WITH schema shared_extensions; 
CREATE EXTENSION if not exists citext WITH schema shared_extensions; 
CREATE EXTENSION if not exists pg_trgm WITH schema shared_extensions;
CREATE EXTENSION if not exists postgis with schema shared_extensions;
