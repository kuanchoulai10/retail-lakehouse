# Deployment

This guide covers the deployment and configuration of a Trino cluster using Helm with the faker connector.

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

Execute `generate-tls-certs.sh` to generate TLS certificate and Kubernetes secret:

```bash
./generate-tls-certs.sh
```

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

`trino-tls-secret.yaml` should look like this:

```yaml title="trino-tls-secret.yaml"
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
LAST DEPLOYED: Fri Jun 13 17:49:52 2025
NAMESPACE: trino
STATUS: deployed
REVISION: 1
NOTES:
Get the application URL by running these commands:
  kubectl --namespace trino port-forward svc/trino 8080:8080
  echo "Visit http://127.0.0.1:8080 to use your application"
```

Show the deployed Trino release:

```
helm list -n trino
```

```
NAME    NAMESPACE       REVISION        UPDATED                                 STATUS          CHART           APP VERSION
trino   trino           1               2025-06-13 18:08:54.435442 +0800 CST    deployed        trino-1.39.1    475    
```

Get the status of all resources in the `trino` namespace:

```bash
kubectl get all -n trino
```

```
NAME                                     READY   STATUS    RESTARTS   AGE
pod/trino-coordinator-6fdfb7bf84-tjwfc   1/1     Running   0          5m38s
pod/trino-worker-777d595c66-dml67        1/1     Running   0          5m38s
pod/trino-worker-777d595c66-pv9h2        1/1     Running   0          5m38s

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

It looks like everything is running fine. The Trino coordinator and worker pods are up and running, and the services are created. Next, we will access the Trino Web UI and CLI to interact with the Trino cluster.

## Accessing Trino

### Web UI

First, we need to port-forward the Trino service to access the Web UI:

```bash
kubectl port-forward svc/trino 8443:8443 --namespace trino
```

Then visit https://127.0.0.1:8443, in the browser, you will see a warning about the self-signed certificate. You can safely ignore this warning for local development purposes.
You can proceed to the Trino Web UI by clicking "Advanced" and then "Accept the Risk and Continue".

![](./static/browser-cert.png)

![](./static/browser-continue.png)

because we have configured Trino to use OAuth 2.0 authentication, you will be redirected to the Google login page.

![](./static/google-login-page.png)

After logging in with your Google account, you will be redirected back to the Trino Web UI.

![](./static/trino-web-ui.png)

### Trino CLI

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

Access the Trino CLI using [the external authentication](https://trino.io/docs/current/client/cli.html#external-authentication-sso):

```bash
trino --server https://127.0.0.1:8443 \
      --external-authentication
```

The detailed behavior is as follows:

- Start the CLI with the `--external-authentication` option and execute a query.
- The CLI starts and connects to Trino.
- A message appears in the CLI directing you to open a browser with a specified URL when the first query is submitted.
- Open the URL in a browser and follow through the authentication process.
- The CLI automatically receives a token.
- When successfully authenticated in the browser, the CLI proceeds to execute the query.
- Further queries in the CLI session do not require additional logins while the authentication token remains valid. Token expiration depends on the external authentication type configuration.
- Expired tokens force you to log in again.


## Cleanup

To remove the Trino cluster:

```bash
helm uninstall trino --namespace trino
kubectl delete namespace trino
```



```
env $(cat .env | xargs) envsubst < values-template.yaml > values.yaml
```