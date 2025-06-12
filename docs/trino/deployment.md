# Trino Cluster Deployment

This guide covers the deployment and configuration of a Trino cluster using Helm with the faker connector.

## Files

- `values.yaml` - Main Helm values file with faker connector and custom configurations
- `test-faker.sql` - Sample SQL queries to test the faker connector


## Prerequisites

- Kubernetes cluster
- Helm 3.x installed
- kubectl configured to access your cluster
- Java 11 minimum requirement for JDBC driver compatibility


## Deployment

Create the trino namespace, we will deploy Trino in this namespace:

```bash
kubectl create namespace trino
```

```
namespace/trino created
```

Execute `generate-tls-certs.sh` to generate TLS certificates and Kubernetes secret:

```bash
./generate-tls-certs.sh
```

```
Creating TLS certificates for Trino...
{==Step 1: Generating keystore with private key and self-signed certificate...==}
針對 CN=coordinator, OU=datalake, O=dataco, L=Sydney, ST=NSW, C=AU 產生有效期 365 天的 2,048 位元 RSA 金鑰組以及自我簽署憑證 (SHA384withRSA)

{==Step 2: Exporting certificate from keystore...==}
憑證儲存在檔案 <.cert/trino.cer>
{==Step 3: Creating truststore and importing certificate...==}
憑證已新增至金鑰儲存庫中
[儲存 .cert/truststore.jks]
{==Step 4: Converting keystore to PKCS12 format...==}
正在將金鑰儲存庫 .cert/keystore.jks 匯入 .cert/trino.p12...
{==Step 5: Extracting PEM format from PKCS12...==}
{==Step 6: Converting certificate to CRT format...==}
{==Step 7: Verifying certificate contents...==}
Certificate details:
            X509v3 Subject Alternative Name: 
                DNS:localhost, DNS:trino, DNS:trino.default, DNS:trino.default.svc, DNS:trino.default.svc.cluster.local, DNS:coordinator, DNS:coordinator.default, DNS:coordinator.default.svc, DNS:coordinator.default.svc.cluster.local, IP Address:127.0.0.1
    Signature Algorithm: sha384WithRSAEncryption
    Signature Value:
        71:4c:cf:17:88:99:10:63:e3:1d:9c:48:76:53:57:52:0a:70:
        9d:f8:1f:77:d6:58:37:c8:fe:0a:b4:75:4f:83:fb:96:ad:df:
        e9:6b:10:32:b2:74:01:2b:8c:3c:ec:ec:fe:e5:f1:1e:77:c8:
        59:81:52:d2:10:54:5f:8c:ae:ce:a5:62:8d:97:38:57:a4:7a:
        3a:8a:b1:db:c2:98:96:0f:1a:ba:37:de:30:92:96:e0:fd:59:
        45:5c:d1:3a:e1:a5:ae:e1:ef:36:b4:e1:a0:36:d3:79:4a:40:
        d6:f5:2e:82:50:bb:f0:30:47:4e:02:8b:a5:45:39:5a:da:24:
{==Step 8: Creating Kubernetes secret...==}
Certificate generation completed successfully!


Generated files in .cert/:
  - {==keystore.jks==} (server keystore for Trino coordinator)
  - {==truststore.jks==} (client truststore for Trino CLI)
  - {==trino.cer==} (certificate in DER format)
  - {==trino.crt==} (certificate in PEM format)
  - {==trino.p12==} (PKCS12 format keystore)
  - {==trino.pem==} (PEM format with private key)
  - {==trino-tls-secret.yaml==} (Kubernetes secret manifest)

To apply the Kubernetes secret, run:
  {==kubectl apply -f .cert/trino-tls-secret.yaml==}

To connect with Trino CLI using HTTPS:
  trino --server https://your-trino-server:8443 --truststore-path .cert/truststore.jks --truststore-password trinoSecurePassword2024
```

`trino-tls-secret.yaml` should look like this:

```yaml title="trino-tls-secret.yaml"
apiVersion: v1
kind: Secret
metadata:
  creationTimestamp: null
  {==name: trino-tls-secret==}
data:
  {==keystore-password==}: xxx
  {==keystore.jks==}: xxx

```

Create Kubernetes secret to mount the TLS certificate:

```bash
kubectl apply -f .cert/trino-tls-secret.yaml --namespace trino
```

```
secret/trino-tls-secret created
```

Add and update the Trino Helm repository:

```bash
helm repo add trino https://trinodb.github.io/charts/
helm repo update
```

Deploy Trino in the `trino` namespace using the provided `values.yaml` file:

```bash
helm install trino trino/trino -f values.yaml --namespace trino
```

```
NAME: trino
LAST DEPLOYED: Wed Jun 11 16:34:42 2025
NAMESPACE: trino
STATUS: {==deployed==}
REVISION: 1
NOTES:
Get the application URL by running these commands:
  kubectl --namespace trino port-forward svc/trino 8080:8080
  echo "Visit http://127.0.0.1:8080 to use your application"
```

```bash
kubectl get all -n trino
```

```
NAME                                    READY   STATUS    RESTARTS   AGE
pod/trino-coordinator-7b44f6957-fmwgm   0/1     Running   0          23s
pod/trino-worker-55b947bf85-dnm7s       0/1     Running   0          23s
pod/trino-worker-55b947bf85-lg6h6       0/1     Running   0          23s

NAME                   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
service/trino          ClusterIP   10.111.85.227   <none>        8080/TCP,8443/TCP   23s
service/trino-worker   ClusterIP   None            <none>        8080/TCP            23s

NAME                                READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/trino-coordinator   0/1     1            0           24s
deployment.apps/trino-worker        0/2     2            0           24s

NAME                                          DESIRED   CURRENT   READY   AGE
replicaset.apps/trino-coordinator-7b44f6957   1         1         0       24s
replicaset.apps/trino-worker-55b947bf85       2         2         0       24s
```

## Accessing Trino

### Web UI

```bash
kubectl port-forward svc/trino 8443:8443 --namespace trino
```

Then visit https://localhost:8443

### Command Line

Download the `trino-cli-476-executable.jar ` Trino CLI executable jar file in [Maven repo](https://repo1.maven.org/maven2/io/trino/trino-cli/)

Rename it to `trino` and make it executable and move it to a directory in your PATH, e.g., `/usr/local/bin`:

```bash
chmod +x trino-cli-476-executable.jar
sudo mv trino-cli-476-executable.jar /usr/local/bin/trino
```

```bash
trino --version
```

```
Trino CLI 476
```

Access the Trino CLI using the generated truststore:

```bash
trino --server https://localhost:8443 \
      --truststore-path .cert/truststore.jks \
      --truststore-password trinoSecurePassword2024
```



## Configuration

The configuration includes:

### Trino Version
The Trino image version is configured as:

```yaml title="values.yaml - Trino Version"
image:
  ...
--8<-- "trino/values.yaml:trino-version"
```

### Worker Configuration
Number of worker nodes:

```yaml title="values.yaml - Worker Configuration"
server:
  ...
--8<-- "trino/values.yaml:worker-config"
```

### Memory Configuration
Both coordinator and worker nodes are configured with 8GB heap size:

**Coordinator Memory:**

```yaml title="values.yaml - Coordinator Memory"
coordinator:
  jvm:
    ...
--8<-- "trino/values.yaml:coordinator-memory"
```

**Worker Memory:**

```yaml title="values.yaml - Worker Memory"
worker:
  jvm:
    ...
--8<-- "trino/values.yaml:worker-memory"
```

### HTTPS Configuration

Once you have generated the certificates using the script, you need to configure the Trino cluster to use HTTPS. The configuration involves several components in the `values.yaml` file:

**Enable HTTPS and Configure Keystore Properties**

The core HTTPS configuration is done through additional config properties:

```yaml title="values.yaml - HTTPS Configuration"
--8<-- "trino/values.yaml:https-config"
```

This configuration:

- Enables HTTPS server with `http-server.https.enabled=true`
- Sets HTTPS port to 8443 (standard alternative HTTPS port)
- Points to the keystore file location inside the container
- Sets the keystore alias (key identifier within the keystore)
- References the keystore password from environment variable

**Environment Variable for Keystore Password**

The keystore password is securely provided through a Kubernetes secret:

```yaml title="values.yaml - HTTPS Environment Variables"
--8<-- "trino/values.yaml:https-env"
```

This configuration:

- Creates an environment variable `KEYSTORE_PASSWORD`
- Sources the password from the `trino-tls-secret` Kubernetes secret
- Uses the `keystore-password` key from that secret

**Expose HTTPS Port in Service**

The coordinator service needs to expose the HTTPS port:

```yaml title="values.yaml - HTTPS Port Configuration"
coordinator:
  ...
--8<-- "trino/values.yaml:https-port"
```

This configuration:

- Exposes port 8443 for HTTPS traffic
- Maps container port 8443 to service port 8443
- Uses TCP protocol for the connection

**Mount TLS Secret as Volume**

The keystore file needs to be mounted into the coordinator container:

```yaml title="values.yaml - TLS Volume Configuration"
coordinator:
  ...
--8<-- "trino/values.yaml:https-volume"
```

This configuration:

- Creates a volume named `trino-tls` from the Kubernetes secret
- References the `trino-tls-secret` which contains the keystore.jks file

**Mount Volume to Container Path**

The TLS volume is mounted to the expected path inside the container:

```yaml title="values.yaml - TLS Volume Mount Configuration"
coordinator:
  ...
--8<-- "trino/values.yaml:https-volume-mount"
```

This configuration:

- Mounts the `trino-tls` volume to `/etc/trino/tls` directory
- Sets read-only access for security
- Makes the keystore.jks file available at `/etc/trino/tls/keystore.jks`






### Fault Tolerant Configuration

<!-- TODO: Fault Tolerant -->
retry-policy=TASK


[Improve query processing resilience](https://trino.io/docs/current/installation/query-resiliency.html)

[Fault-tolerant execution](https://trino.io/docs/current/admin/fault-tolerant-execution.html)


### Catalogs Configuration

The following catalogs are configured:

```yaml title="values.yaml - Catalogs Configuration"
--8<-- "trino/values.yaml:catalogs-config"
```

This includes:

- `faker` - Generates fake data for testing
- `tpch` - TPC-H benchmark data  
- `tpcds` - TPC-DS benchmark data

## Cleanup

To remove the Trino cluster:

```bash
helm uninstall trino --namespace trino
# Optionally delete the namespace
kubectl delete namespace trino
```

