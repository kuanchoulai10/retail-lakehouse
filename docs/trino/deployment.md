# Deployment

This guide covers the deployment and configuration of a Trino cluster using Helm with the faker connector.

## Prerequisites

- Kubernetes cluster
- Helm 3.x installed
- `kubectl` configured to access your cluster
- Java 11 minimum requirement for JDBC driver compatibility
- Rename `.env.template` file to `.env` and configure all the variables in the file

??? info ".env"

    - **OAUTH2_CLIENT_ID**  
      The client ID for OAuth 2.0 authentication, used to enable Google login for the Trino Web UI.  
      Referenced in `values-template.yaml` as `http-server.authentication.oauth2.client-id`.

    - **OAUTH2_CLIENT_SECRET**  
      The client secret for OAuth 2.0 authentication, paired with the client ID for secure login.  
      Used in `values-template.yaml` as `http-server.authentication.oauth2.client-secret`.

    - **INTERNAL_SHARED_SECRET**  
      A secret string for internal communication security between Trino nodes.  
      Used in `values-template.yaml` as `internal-communication.shared-secret`.

    - **SA_INPUT_PATH**  
      Path to the service account JSON file for Google Cloud authentication.  
      Used by `generate-trino-bigquery-secret.sh` to create the BigQuery service account secret.

    - **PROJECT_ID**  
      The Google Cloud project ID, required for the BigQuery connector in Trino.  
      Used in `values-template.yaml` as `bigquery.project-id`.

    - **AWS_ACCESS_KEY**  
      AWS access key for authenticating to AWS services (S3, Glue, etc.).  
      Used in `values-template.yaml` for S3 and Glue access, and for exchange manager S3 configuration.

    - **AWS_SECRET_KEY**  
      AWS secret key, paired with the access key for AWS authentication.  
      Used in `values-template.yaml` for S3, Glue, and exchange manager S3 configuration.

    - **AWS_REGION**  
      The AWS region where your S3 buckets and Glue Data Catalog are located.  
      Used in `values-template.yaml` for S3, Glue, and exchange manager S3 configuration.

    - **ICEBERG_S3_URL**  
      The S3 URL (bucket path) for storing Iceberg table data.  
      Used in `values-template.yaml` as `hive.metastore.glue.default-warehouse-dir`.

    - **EXCHANGE_S3_URLS**  
      S3 URLs for Trino's exchange manager, which handles intermediate data during distributed query execution.  
      Used in `values-template.yaml` as `exchangeManager.base-directories`.

    These variables are substituted into the Trino Helm values file and Kubernetes secrets using `envsubst` to configure authentication, storage, and cloud integration for your Trino deployment.

## Deployment

Create the trino namespace, we will deploy Trino in this namespace:

```bash
kubectl create namespace trino
```

??? info "Result"

    ```
    namespace/trino created
    ```

### Setting up TLS Certificates

Execute `generate-tls-certs.sh` to generate TLS certificate and Kubernetes secret:

```bash
./generate-tls-certs.sh
```

??? info "Result"

    ```
    Creating TLS certificates for Trino...
    Step 1: Creating Private Key...
    Step 2: Creating Certificate...
    Step 3: Combining Private Key and Certificate...
    Step 4: Creating Kubernetes secret...
    Certificate generation completed successfully!

    Generated files in .cert/:
      - {==trino-dev.pem==} (with private key and certificate)
      - {==trino-tls-secret.yaml==} (Kubernetes secret manifest)
    ```

Once executed, the `trino-tls-secret.yaml` file will have the following structure:

??? info "trino-tls-secret.yaml"

    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      creationTimestamp: null
      name: trino-tls-secret
    data:
      {==trino-dev.pem==}: xxx
    ```

Create Kubernetes secret to mount the TLS certificate:

```bash
kubectl apply -f .cert/trino-tls-secret.yaml --namespace trino
```

### Configuring BigQuery Service Account

Generate the BigQuery service account secret for Trino:

```bash
env $(cat .env | xargs) envsubst < generate-trino-bigquery-secret.sh | bash
```

After running the script, you will have a Kubernetes secret manifest file named `trino-bigquery-secret.yaml` in the current directory. Then apply the secret to the Kubernetes cluster:

```bash
kubectl apply -f ./trino-bigquery-secret.yaml --namespace trino
```

### Installing Trino

First, add and update the Trino Helm repository:

```bash
helm repo add trino https://trinodb.github.io/charts/
helm repo update
```

Next, generate the Trino Helm values file using variables from the `.env` file:

```bash
env $(cat .env | xargs) envsubst < values-template.yaml > values.yaml
```

Now, deploy Trino in the `trino` namespace using the provided `values.yaml` file:

```bash
helm install trino trino/trino -f values.yaml --namespace trino
```

??? info "Result"

    ```
    NAME: trino
    LAST DEPLOYED: Fri Jun 13 17:49:52 2025
    NAMESPACE: trino
    STATUS: {==deployed==}
    REVISION: 1
    NOTES:
    Get the application URL by running these commands:
      kubectl --namespace trino port-forward svc/trino 8080:8080
      echo "Visit http://127.0.0.1:8080 to use your application"
    ```

### Verifying the Deployment

After the installation completes, verify that Trino has been deployed successfully. Show the deployed Trino release:

```
helm list -n trino
```

??? info "Result"

    ```
    NAME    NAMESPACE       REVISION        UPDATED                                 STATUS          CHART           APP VERSION
    trino   trino           1               2025-06-13 18:08:54.435442 +0800 CST    {==deployed==}        trino-1.39.1    475    
    ```

Then, check the status of all resources in the `trino` namespace:

```bash
kubectl get all -n trino
```

??? info "Result"

    ```
    NAME                                     READY   STATUS    RESTARTS   AGE
    pod/trino-coordinator-6fdfb7bf84-tjwfc   1/1     {==Running==}   0          5m38s
    pod/trino-worker-777d595c66-dml67        1/1     {==Running==}   0          5m38s
    pod/trino-worker-777d595c66-pv9h2        1/1     {==Running==}   0          5m38s

    NAME                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
    service/trino          ClusterIP   10.99.208.168   <none>        8080/TCP,{==8443/TCP==}   5m38s
    service/trino-worker   ClusterIP   None            <none>        8080/TCP            5m38s

    NAME                                READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/trino-coordinator   1/1     1            1           5m38s
    deployment.apps/trino-worker        2/2     2            2           5m38s

    NAME                                           DESIRED   CURRENT   READY   AGE
    replicaset.apps/trino-coordinator-6fdfb7bf84   1         1         1       5m38s
    replicaset.apps/trino-worker-777d595c66        2         2         2       5m38s
    ```

Perfect! The deployment is successful. As you can see, the Trino coordinator and worker pods are up and running, and all services have been created correctly. With the cluster now operational, we can proceed to access the Trino Web UI and CLI to interact with the cluster.

## Accessing Trino

Now that Trino is successfully deployed and running, you can access it through both the Web UI and CLI. The cluster is configured with OAuth 2.0 authentication and TLS encryption for secure access.

### Web UI

To access the Trino Web UI, start by port-forwarding the Trino service to your local machine:

```bash
kubectl port-forward svc/trino 8443:8443 --namespace trino
```

Once the port forwarding is active, open your browser and navigate to `https://127.0.0.1:8443`. Since we're using a self-signed certificate for development purposes, your browser will display a security warning. This is expected behavior and safe to bypass in a development environment.

To proceed, click **"Advanced"** and then **"Accept the Risk and Continue"** (the exact wording may vary depending on your browser).

![](./static/browser-cert.png)

![](./static/browser-continue.png)

Since OAuth 2.0 authentication is enabled, you'll be automatically redirected to the Google login page for authentication.

![](./static/google-login-page.png)

After logging in with your Google account, you will be redirected back to the Trino Web UI.

![](./static/trino-web-ui.png)

Once authenticated successfully, you'll be redirected back to the Trino Web UI where you can monitor queries, view cluster status, and manage your Trino environment.

### Trino CLI

For command-line access to Trino, you'll need to download and install the Trino CLI tool.

First, download the `trino-cli-476-executable.jar` file from the [Maven repository](https://repo1.maven.org/maven2/io/trino/trino-cli/).

Next, rename the file to `trino`, make it executable, and move it to a directory in your PATH (such as `/usr/local/bin`):

```bash
chmod +x trino-cli-476-executable.jar
sudo mv trino-cli-476-executable.jar /usr/local/bin/trino
```

Verify the installation by checking the version:

```bash
trino --version
```

??? info "Result"

    ```
    Trino CLI 476
    ```

To connect to your Trino cluster, use the CLI with [external authentication](https://trino.io/docs/current/client/cli.html#external-authentication-sso) enabled:

```bash
trino --server https://127.0.0.1:8443 \
      --external-authentication \
      --insecure \
      --user "user@example.com"
```

**Authentication Flow:**

The CLI authentication process works as follows:

- Start the CLI with the `--external-authentication` option and execute a query.
- The CLI starts and connects to Trino.
- A message appears in the CLI directing you to open a browser with a specified URL when the first query is submitted.
- Open the URL in a browser and follow through the authentication process.
- The CLI automatically receives a token.
- When successfully authenticated in the browser, the CLI proceeds to execute the query.
- Further queries in the CLI session do not require additional logins while the authentication token remains valid. Token expiration depends on the external authentication type configuration.
- Expired tokens force you to log in again.

This authentication method ensures secure access to your Trino cluster while maintaining ease of use for interactive queries.

## Cleanup

To remove the Trino cluster:

```bash
helm uninstall trino --namespace trino
kubectl delete namespace trino
```