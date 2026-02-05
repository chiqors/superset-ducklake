-- SELECT
--     *
-- FROM read_parquet(
--     'gs://oucru-id-cloud_analytics/organization.parquet'
-- )
-- LIMIT 5

-- CREATE TABLE organization AS
-- SELECT *
-- FROM read_parquet('gs://oucru-id-cloud_analytics/organization.parquet');

-- SHOW TABLES;

-- SELECT * FROM organization LIMIT 2;

-- SELECT
--   id,
--   name,
-- FROM organization
-- LIMIT 10;