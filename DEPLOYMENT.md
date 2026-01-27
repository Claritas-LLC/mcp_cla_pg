# Deployment Guide for PostgreSQL MCP Server

This guide provides instructions for deploying the PostgreSQL MCP Server to various environments, including local development, Docker, Azure Container Apps, and AWS ECS.

## 📋 Prerequisites

Before deploying, ensure you have:
1.  **PostgreSQL Database**: A running instance (version 9.6+).
2.  **Connection String**: A valid `DATABASE_URL` (e.g., `postgresql://user:pass@host:5432/dbname`).
3.  **Container Registry**: A place to push your Docker image (e.g., Docker Hub, ACR, ECR) if deploying to the cloud.

---

## 💻 Local Development

### Option 1: Python (uv)
Best for rapid development and testing.

```bash
# 1. Install dependencies
uv sync

# 2. Set environment variables
$env:DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"

# 3. Run server
uv run mcp-postgres
```

### Option 2: Docker Compose
Best for testing the containerized environment locally.

```bash
# 1. Update docker-compose.yml with your database credentials if needed

# 2. Build and run
docker compose up --build
```

---

## 🐳 Building the Docker Image

To deploy to the cloud, you first need to build and push the image.

```bash
# Build
docker build -t harryvaldez/mcp-postgres:latest .

# Push
docker push harryvaldez/mcp-postgres:latest
```

---

## ☁️ Azure Container Apps (ACA)

We provide a Bicep template (`deploy/azure-aca.bicep`) for easy deployment to Azure.

### Features
*   **Serverless**: Scale to zero capability (though minReplicas=1 is recommended).
*   **Secure**: Secrets management for `DATABASE_URL`.
*   **Health Checks**: Built-in liveness and readiness probes.

### Deployment Steps

1.  **Login to Azure**:
    ```bash
    az login
    ```

2.  **Deploy using CLI**:
    ```bash
    az deployment group create \
      --resource-group <YourResourceGroup> \
      --template-file deploy/azure-aca.bicep \
      --parameters \
        containerImage="harryvaldez/mcp-postgres:latest" \
        databaseUrl="postgresql://user:pass@host:5432/dbname" \
        allowWrite=false
    ```

---

## ☁️ AWS ECS (Fargate)

We provide a CloudFormation template (`deploy/aws-ecs.yaml`) for deploying to AWS Fargate.

### Features
*   **Serverless Compute**: No EC2 instances to manage.
*   **Logging**: Integrated with CloudWatch Logs.
*   **IAM Roles**: Least privilege access for ECS tasks.

### Deployment Steps

1.  **Upload Template**: Go to the AWS CloudFormation console and upload `deploy/aws-ecs.yaml`.

2.  **Configure Parameters**:
    *   **VpcId**: Select your VPC (must have connectivity to your RDS/Database).
    *   **SubnetIds**: Select private subnets (recommended).
    *   **ContainerImage**: Your ECR image URI.
    *   **DatabaseUrl**: Your connection string.

3.  **Deploy**: Create the stack.

---

## 🔒 Security Checklist

When deploying to production, verify the following:

1.  **Authentication**: If using HTTP transport, enable Azure AD or another auth provider.
    *   Set `FASTMCP_AUTH_TYPE=azure-ad`.
    *   Configure Tenant/Client IDs.
2.  **Network**: Ensure the container can reach your PostgreSQL database.
    *   **Azure**: Use VNet injection if using Azure Database for PostgreSQL.
    *   **AWS**: Ensure Security Groups allow inbound port 5432 from the ECS tasks.
3.  **Secrets**: Never hardcode passwords. Use Azure Key Vault or AWS Secrets Manager where possible (templates currently use environment variables/secrets).
4.  **Write Access**: Keep `MCP_ALLOW_WRITE=false` unless explicitly required for maintenance tasks.

## 🔄 CI/CD (GitHub Actions)

To automate deployment, you can set up a GitHub Action workflow that:
1.  Triggers on push to `main`.
2.  Builds the Docker image.
3.  Pushes to ACR/ECR.
4.  Runs `az containerapp update` or updates the CloudFormation stack.
