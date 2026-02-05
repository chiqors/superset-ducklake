# Superset DuckLake Helm Chart

A production-ready Helm chart for deploying Apache Superset with DuckLake integration (DuckDB + Postgres + GCS).

## Features

- **Stateless Architecture**: Deploys Superset Web and Workers independently.
- **High Availability**: Supports multiple replicas for web and worker components.
- **Async Execution**: Integrated Celery workers for handling long-running queries.
- **External Dependencies**: Designed to connect to managed Postgres and Redis/Valkey services.
- **Multi-Cloud Storage**: Supports both Google Cloud Storage (GCS) and Amazon S3 / MinIO for DuckLake data.
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
