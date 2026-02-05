# Superset DuckLake Helm Chart

A production-ready Helm chart for deploying Apache Superset with DuckLake integration (DuckDB + Postgres + GCS).

## Features

- **Stateless Architecture**: Deploys Superset Web and Workers independently.
- **High Availability**: Supports multiple replicas for web and worker components.
- **Async Execution**: Integrated Celery workers for handling long-running queries.
- **External Dependencies**: Designed to connect to managed Postgres and Redis/Valkey services.
- **Multi-Cloud Storage**: Supports both Google Cloud Storage (GCS) and Amazon S3 / MinIO for DuckLake data.
- **BigQuery Integration**: Native support for querying BigQuery datasets through DuckDB BigQuery plugin.
- **Cloud Native**: Supports Kubernetes secrets, configmaps, and resource limits.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- External PostgreSQL Database (for metadata)
- External Redis or Valkey (for caching and message broker)

## Installation

1.  **Add the repository** (if hosted) or navigate to the chart directory:
    ```bash
    cd charts/superset
    ```

2.  **Configure `values.yaml`**:
    Create a `my-values.yaml` file with your external service connection details:

    ```yaml
    # my-values.yaml
    
    # Image from GHCR
    image:
      repository: ghcr.io/your-org/superset
      tag: latest
    
    # External Postgres (Superset Metadata)
    externalPostgres:
      host: "my-postgres.rds.amazonaws.com"
      port: 5432
      database: "superset"
      username: "superset_user"
      password: "secure_password"
    
    # External Postgres (DuckLake Metadata)
    ducklakePostgres:
      host: "my-postgres.rds.amazonaws.com"
      port: 5432
      database: "ducklake_analytics"
      username: "superset_user"
      password: "secure_password"
    
    # External Redis/Valkey (Required)
    externalRedis:
      host: "my-valkey.elasticache.amazonaws.com"
      port: 6379
      celeryDb: "0"
      resultsDb: "1"
      cacheDb: "2"
    
    # DuckLake Storage Configuration
    superset:
      # Choose 'gcs' or 's3'
      storageDriver: "s3"
      
      # If using S3:
      s3:
        accessKeyId: "AWS_ACCESS_KEY"
        secretAccessKey: "AWS_SECRET_KEY"
        bucketPath: "s3://my-data-bucket/"
        region: "us-east-1"
        # Optional: endpoint for MinIO
        # endpoint: "minio:9000"
    
      # If using GCS:
      # storageDriver: "gcs"
      # gcs:
      #   keyId: "GCS_ACCESS_KEY"
      #   secret: "GCS_SECRET"
      #   bucketPath: "gs://my-data-bucket/"
    
    # Scaling
    worker:
      replicas: 2
    ```

3.  **Install the Chart**:
    ```bash
    helm install superset . -f my-values.yaml \
      --set commonLabels.environment=production
    ```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Docker image repository | `ghcr.io/...` |
| `image.tag` | Docker image tag | `latest` |
| `service.type` | Kubernetes Service type | `ClusterIP` |
| `worker.enabled` | Enable Celery workers | `true` |
| `worker.replicas` | Number of worker replicas | `1` |
| `externalPostgres.host` | Postgres hostname (Superset Metadata) | `postgres-host` |
| `ducklakePostgres.host` | Postgres hostname (DuckLake Metadata) | `postgres-host` |
| `externalRedis.host` | Redis/Valkey hostname | `valkey-host` |
| `commonLabels` | Labels to apply to all resources | `{}` |
| `namespaceOverride` | Override the release namespace | `""` |

## Architecture

This chart deploys:
- **Deployment (Web)**: Superset web server (gunicorn).
- **Deployment (Worker)**: Celery worker for async tasks.
- **ConfigMap**: Non-sensitive configuration (env vars).
- **Secret**: Sensitive configuration (passwords, keys).
- **Service**: Internal ClusterIP for the web server.

It **does not** deploy databases or caches. You must provide connection details for:
- PostgreSQL (Metadata)
- Redis/Valkey (Cache & Broker)

## CI/CD

This chart is automatically packaged and pushed to GHCR OCI registry via GitHub Actions when a new tag (e.g., `v1.0.0`) is pushed to the repository.

## BigQuery Configuration

This Helm chart supports DuckDB BigQuery plugin integration, allowing you to query BigQuery datasets through DuckDB.

### Prerequisites

1. A Google Cloud Platform (GCP) project with BigQuery API enabled
2. A service account with appropriate BigQuery permissions:
   - `bigquery.jobs.create`
   - `bigquery.tables.get`
   - `bigquery.tables.list`
   - `bigquery.datasets.get`
3. Service account JSON key file

### Configuration Options

Configure BigQuery in your `values.yaml`:

```yaml
superset:
  bigquery:
    enabled: true
    projectId: "your-gcp-project-id"
    # All datasets in the project will be accessible via bq.dataset_name.table_name
    serviceAccountJson: ""  # Base64 encoded or plain JSON string
    # OR use existing secret
    existingSecret: ""
    existingSecretKey: "service-account.json"
```

### Setup Methods

#### Method 1: Inline Service Account JSON (Development)

1. Encode your service account JSON:
```bash
cat service-account.json | base64
```

2. Add to `values.yaml`:
```yaml
superset:
  bigquery:
    enabled: true
    projectId: "my-project"
    serviceAccountJson: "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsC..."
```

3. Install/upgrade the chart:
```bash
helm upgrade --install superset ./charts/superset -f values.yaml
```

#### Method 2: Using Existing Kubernetes Secret (Production - Recommended)

1. Create a Kubernetes secret with your service account JSON:
```bash
kubectl create secret generic bigquery-sa-secret \
  --from-file=service-account.json=./path/to/service-account.json \
  -n your-namespace
```

2. Reference the secret in `values.yaml`:
```yaml
superset:
  bigquery:
    enabled: true
    projectId: "my-project"
    existingSecret: "bigquery-sa-secret"
    existingSecretKey: "service-account.json"
```

3. Install/upgrade the chart:
```bash
helm upgrade --install superset ./charts/superset -f values.yaml
```

#### Method 3: Using Helm Secrets or SOPS (Production - Most Secure)

1. Encrypt your service account JSON using helm-secrets:
```bash
helm secrets enc values-secret.yaml
```

2. Add encrypted values to `values-secret.yaml`:
```yaml
superset:
  bigquery:
    enabled: true
    projectId: "my-project"
    serviceAccountJson: ENC[AES256_GCM,data:...]
```

3. Install with secrets:
```bash
helm secrets upgrade --install superset ./charts/superset -f values.yaml -f values-secret.yaml
```

### Using BigQuery in DuckDB

Once configured, the BigQuery extension will be available in DuckDB. The service account JSON is mounted at:
```
/app/secrets/bigquery/service-account.json
```

Environment variables set:
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON
- `BIGQUERY_ENABLED`: "true"
- `BIGQUERY_PROJECT_ID`: Your GCP project ID

### Verification

After deployment, verify BigQuery is configured:

```bash
# Check if secret is mounted
kubectl exec -it deployment/superset-superset -- ls -la /app/secrets/bigquery/

# Check environment variables
kubectl exec -it deployment/superset-superset -- env | grep BIGQUERY
```

### Security Best Practices

1. **Never commit service account JSON to version control**
   - Add `service-account*.json` to `.gitignore`
   - Use encrypted secrets management

2. **Use least privilege principle**
   - Grant only necessary BigQuery permissions
   - Use separate service accounts for different environments

3. **Rotate credentials regularly**
   - Set up key rotation policy
   - Update secrets when rotating keys

4. **Consider Workload Identity (GKE)**
   - For GKE clusters, use Workload Identity instead of service account keys
   - More secure and eliminates key management

5. **Use existing secrets in production**
   - Avoid inline `serviceAccountJson` in production
   - Use `existingSecret` with proper RBAC

### Troubleshooting

**Issue: Secret not mounted**
```bash
# Check if secret exists
kubectl get secret superset-bigquery-sa -n your-namespace

# Describe pod to see mount issues
kubectl describe pod superset-superset-xxx -n your-namespace
```

**Issue: Permission denied**
```bash
# Check file permissions
kubectl exec -it deployment/superset-superset -- ls -la /app/secrets/bigquery/

# Should show: -r-------- (0400)
```

**Issue: BigQuery authentication fails**
- Verify service account has BigQuery permissions
- Check project ID is correct
- Ensure BigQuery API is enabled in GCP project
- Validate JSON file is not corrupted

### Example: Complete Configuration

```yaml
superset:
  bigquery:
    enabled: true
    projectId: "my-analytics-project"
    # All datasets in the project will be accessible
    existingSecret: "bigquery-credentials"
    existingSecretKey: "service-account.json"
```

### Integration with DuckDB

The BigQuery project is automatically attached when DuckDB initializes using the ATTACH method. This provides access to ALL datasets in your project.

#### Querying BigQuery Tables

Once configured, you can query any table across all datasets in your project:

```sql
-- Query tables from any dataset in the project
SELECT * FROM bq.dataset_name.table_name;

-- Example: Query from multiple datasets
SELECT
  a.column1,
  b.column2
FROM bq.analytics.users a
JOIN bq.marketing.campaigns b ON a.id = b.user_id;

-- Discover available datasets and tables
SHOW ALL TABLES;

-- List tables in a specific dataset
SELECT * FROM information_schema.tables
WHERE table_schema = 'dataset_name';
```

#### Key Features

- **Access All Datasets**: The ATTACH method provides access to all datasets in the project via `bq.dataset_name.table_name` syntax
- **No Dataset Restrictions**: Query any dataset without additional configuration
- **Cross-Dataset Queries**: Easily join tables across different datasets
- **Discovery**: Use `SHOW ALL TABLES` to discover available datasets and tables

For more information on DuckDB BigQuery plugin, see: https://github.com/hafenkran/duckdb-bigquery
