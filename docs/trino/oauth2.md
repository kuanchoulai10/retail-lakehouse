# Configure OAuth 2.0 Authentication

Trino can be configured to enable OAuth 2.0 authentication over HTTPS for the Web UI and the JDBC driver. 

Using **TLS and HTTPS for Trino Clients** and a **configured shared secret** is required for OAuth 2.0 authentication.

<figure markdown="span">
  ![](./static/trino.diagram.svg){width="500"}
</figure>

## Configure TLS/HTTPS

Trino runs with no security by default. This allows you to connect to the server using URLs that specify the HTTP protocol when using the Trino CLI, the Web UI, or other clients.

this is about Trino Client and Trino coordinator communication (blue lines) , not about the internal communication between Trino nodes.

To configure Trino with TLS support, consider two alternative paths:

- Use **the load balancer or proxy** at your site or cloud environment to terminate TLS/HTTPS. This approach is the simplest and strongly preferred solution.
- Secure **the Trino server directly**. This requires you to obtain a valid certificate, and add it to the Trino coordinator’s configuration.

Since we are deploying Trino in a local Kubernetes cluster, **we will use the second approach and configure Trino to run with TLS/HTTPS directly with self-signed certificates**.


### Automated Certificate Generation

Use the provided script to automatically generate all necessary certificates and files:

```bash
./generate-tls-certs.sh
```

The automated script performs the following steps. Each step can also be executed manually if needed:

**Step 1: Create Private Key**

```bash
--8<-- "retail-lakehouse/trino/generate-tls-certs.sh:create-private-key"
```

What this does:

- Uses RSA algorithm to generate a 2048-bit private key
- Saves the private key to `.cert/private.key`
- This private key will be used to create the self-signed certificate

**Step 2: Create Self-Signed Certificate**

```bash
--8<-- "retail-lakehouse/trino/generate-tls-certs.sh:create-certificate"
```

What this does:

- Creates a new self-signed X.509 certificate using the private key
- Uses the OpenSSL configuration file (`openssl.cnf`) for certificate settings
- Certificate is valid for 365 days
- Applies `v3_req` extensions which include Subject Alternative Names (SAN)
- The certificate hostname and SAN entries are configured in `openssl.cnf`
- Saves the certificate to `.cert/certificate.crt`

```ini title="openssl.cnf"
--8<-- "retail-lakehouse/trino/openssl.cnf"
```

**Step 3: Combine Private Key and Certificate into PEM Format**

```bash
--8<-- "retail-lakehouse/trino/generate-tls-certs.sh:combine"
```

What this does:

- Combines the private key and certificate into a single PEM file
- Creates `.cert/trino-dev.pem` containing both private key and certificate
- This combined PEM file is commonly used by applications that need both components
- Note: This file contains the private key and must be protected properly

**Step 4: Create Kubernetes Secret Manifest**

```bash
--8<-- "retail-lakehouse/trino/generate-tls-certs.sh:create-k8s-secret"
```

What this does:

- Generates a Kubernetes secret YAML manifest file
- Contains the `trino-dev.pem` file for deployment
- Uses `--dry-run=client` to generate the YAML without applying it to the cluster
- The secret can be applied directly to the Kubernetes cluster with `kubectl apply`

After running the script, you will find the generated files in the `.cert/` directory, the Kubernetes secret manifest file will be named `trino-tls-secret.yaml` and it should look like this:

```yaml title="trino-tls-secret.yaml"
apiVersion: v1
kind: Secret
metadata:
  creationTimestamp: null
  name: trino-tls-secret
data:
  {==trino-dev.pem==}: xxx
```

### Mount the TLS Certificate

To utilize the generated TLS certificate in your Trino deployment, create a Kubernetes secret and mount it to the coordinator's `/etc/trino/tls` directory.

```bash
kubectl apply -f .cert/trino-tls-secret.yaml --namespace trino
```


```yaml title="trino/values-template.yaml coordinator" linenums="1" hl_lines="1 10-13"
--8<-- "retail-lakehouse/trino/values-template.yaml:coordinator"
```

Next, configure the coordinator to use the TLS certificate by specifying its location in the `http-server.https.keystore.path` setting:

```yaml title="trino/values-template.yaml server" linenums="1" hl_lines="1 5 8"
--8<-- "retail-lakehouse/trino/values-template.yaml:server"
```

### Enable and Expose the HTTPS Endpoint

To activate HTTPS in Trino, configure the `http-server.https.enabled` setting to `true` and specify the `http-server.https.port` (typically `8443`). Additionally, expose this port through the Kubernetes service configuration.

```yaml title="trino/values-template.yaml server" linenums="1" hl_lines="1 6 7"
--8<-- "retail-lakehouse/trino/values-template.yaml:server"
```

```yaml title="trino/values-template.yaml coordinator" linenums="1" hl_lines="1 14-19"
--8<-- "retail-lakehouse/trino/values-template.yaml:coordinator"
```

## Secure Internal Communication

To enhance security, the Trino cluster supports secure internal communication (red lines) between nodes through authentication mechanisms, with optional TLS encryption for additional protection.

Configure the shared secret by setting the same value in the config.properties file across all cluster nodes (both coordinator and workers):

```
internal-communication.shared-secret=<secret>
```

A large random key is recommended, and can be generated with the following Linux command:

```
openssl rand 512 | base64
```


```yaml title="trino/values-template.yaml additionalConfigProperties" linenums="1" hl_lines="1 2"
--8<-- "retail-lakehouse/trino/values-template.yaml:additionalConfigProperties"
```

The configurations under `additionalConfigProperties` will impact all the nodes in the Trino Cluster.

## Create Google OAuth 2.0 Client

Since we're using Google as our OAuth2 provider, we'll need to set up a Google OAuth 2.0 client. This is a straightforward process, but there are a few specific configuration details to keep in mind for Trino.

Here are the key configuration settings you'll need:

- **Application Type**: Web application
- **Name**: Trino (It will be only used in the Google Cloud Console for identification purposes)
- **Audience**: Set to **internal** (Typically, Trino is used within an organization, so this setting is appropriate)
- **Authorized Redirect URIs**: Add these two URLs:
    - `https://127.0.0.1:8443/oauth2/callback`
    - `https://127.0.0.1:8443/ui/logout/logout.html`

After createing the OAuth 2.0 client, you will be provided with a **client ID** and a **client secret** and you will need to copy these values into the Trino configuration.

## Configure OAuth 2.0 Authentication

To enable OAuth 2.0 authentication in Trino, you will need to configure the OAuth2 properties in the Trino coordinator, which include the client ID, client secret, and authorization server URL. To enable OAuth 2.0 authentication for the Web UI, you also need to set the authentication type of the Web UI to `oauth2`.

```yaml title="trino/values-template.yaml server" linenums="1" hl_lines="1 3-5 8-12"
--8<-- "retail-lakehouse/trino/values-template.yaml:server"
```

Trino supports reading the Authorization Server configuration from the OIDC provider configuration metadata document. During coordinator startup, Trino retrieves this document and uses the provided values to set the corresponding OAuth2 authentication properties, eliminating the need for additional configuration setup.

For Google configuration metadata document, see [here](https://accounts.google.com/.well-known/openid-configuration).

## References
- [TLS and HTTPS](https://trino.io/docs/current/security/tls.html)
- [Secure internal communication](https://trino.io/docs/current/security/internal-communication.html)
- [OAuth 2.0 authentication](https://trino.io/docs/current/security/oauth2.html)