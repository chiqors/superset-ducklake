# Secrets Directory

This directory is used to store sensitive credential files for local development with Docker Compose.

## BigQuery Service Account

To use BigQuery with DuckDB:

1. Place your Google Cloud service account JSON file here:
   ```
   secrets/bigquery-sa.json
   ```

2. Update your `.env` file:
   ```bash
   BIGQUERY_ENABLED=true
   BIGQUERY_PROJECT_ID=your-gcp-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/bigquery-sa.json
   ```

   **Note**: The BigQuery integration uses the ATTACH method, which provides access to **ALL datasets** in your project. You can query any table using the syntax: `bq.dataset_name.table_name`

3. Restart your containers:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Security Notes

- **Never commit service account JSON files to version control**
- This directory is ignored by `.gitignore`
- Files are mounted as read-only (`:ro`) in containers
- Use separate service accounts for development and production

## File Structure

```
secrets/
├── README.md                 # This file
└── bigquery-sa.json         # Your BigQuery service account (not committed)
```
