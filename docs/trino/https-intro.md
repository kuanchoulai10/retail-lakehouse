# Introduction to HTTPS in Trino

When you connect to Trino over HTTPS, you're creating a secure, encrypted connection. This security relies on certificates and trust relationships.

## What are TLS certificates?

Think of a TLS certificate like a digital ID card for your Trino server. It proves the server is legitimate and allows encrypted communication. The certificate contains the server's public key and identifying information.

## Certificate Authorities (CAs)

A Certificate Authority is like a trusted notary that validates server identities. Well-known CAs include Let's Encrypt and DigiCert. If your Trino server has a certificate from a recognized CA, clients will trust it automatically.

## Self-signed certificates

Sometimes Trino servers use self-signed certificates (created by the server itself, not a CA). Your client won't trust these by default and you'll see SSL errors. To fix this, you need to explicitly tell your client to trust the certificate using a truststore.

## What is a truststore?

A truststore is simply a file containing certificates you trust. It's like a contact list of "safe" servers. Java applications use .jks files for truststores.

## When do you need a truststore?

You'll need to provide a truststore when:

- Connecting to Trino over HTTPS
- The server uses a self-signed certificate
- You see "unable to find valid certification path" errors

## Automated Certificate Generation

Use the provided script to automatically generate all necessary certificates and files:

```bash
./generate-tls-certs.sh
```

The automated script performs the following steps. Each step can also be executed manually if needed:

**Step 1: Generate Keystore (containing private key and certificate)**

```bash
--8<-- "trino/generate-tls-certs.sh:generate-keystore"
```

What this does:

- Uses RSA algorithm to create a public-private key pair
- Creates a self-signed certificate in keystore.jks
- Sets CN=coordinator as the certificate hostname for TLS verification
- SAN (Subject Alternative Name) contains Kubernetes DNS names and IPs that this certificate can serve
- keystore.jks is used by Trino Coordinator when enabling HTTPS
- storepass sets the keystore access password

**Step 2: Export certificate from Keystore (without private key)**

```bash
--8<-- "trino/generate-tls-certs.sh:export-certificate"
```

What this does:

- Exports the server's public certificate from the keystore
- The exported .cer file is used by client applications (like Trino CLI) to create truststore

**Step 3: Create Truststore and import certificate**

```bash
--8<-- "trino/generate-tls-certs.sh:create-truststore"
```

What this does:

- Creates a new truststore.jks file (or imports into existing one)
- Adds the server's .cer certificate to the trust list
- This truststore is used by Trino CLI (or other clients) to trust the Trino Coordinator's HTTPS certificate

**Step 4: Convert keystore to PKCS12 format (cross-platform support)**

```bash
--8<-- "trino/generate-tls-certs.sh:convert-pkcs12"
```

What this does:

- Converts Java-specific .jks format to .p12 (PKCS#12) format
- .p12 is cross-platform (OpenSSL, Nginx, Apache can all use it) encrypted certificate container

**Step 5: Extract PEM format from PKCS12 (common for OpenSSL)**

```bash
--8<-- "trino/generate-tls-certs.sh:extract-pem"
```

What this does:

- Extracts .p12 and outputs as .pem file (contains private key and certificate)
- This is useful for services that need PEM format (like Nginx)
- Note: This .pem contains private key, must be protected properly

**Step 6: Convert .cer certificate to common .crt format**

```bash
--8<-- "trino/generate-tls-certs.sh:convert-crt"
```

What this does:

- Converts DER (binary format) certificate to PEM (text format) certificate .crt
- .crt and .pem are essentially the same format, just different extensions used by different systems

**Step 7: Verify certificate contents**

```bash
--8<-- "trino/generate-tls-certs.sh:verify-certificate"
```

What this does:

- Exports certificate from keystore (binary DER format) and converts to text format
- openssl x509 -text parses certificate content (validity dates, hostnames, SAN)

**Step 8: Create Kubernetes secret manifest**

```bash
--8<-- "trino/generate-tls-certs.sh:create-k8s-secret"
```

What this does:

- Generates a Kubernetes secret YAML manifest file
- Contains the keystore.jks file and password for deployment
- Can be applied directly to Kubernetes cluster
