#!/bin/bash

set -euo pipefail


CERT_DIR=".cert"
mkdir -p "$CERT_DIR"
rm -f "$CERT_DIR"/*


echo "Creating TLS certificates for Trino..."


# --8<-- [start:create-private-key]
echo "Step 1: Creating Private Key..."
openssl genrsa -out $CERT_DIR/private.key 2048 > /dev/null
echo "Step 1: Completed."
# --8<-- [end:create-private-key]


# --8<-- [start:create-certificate]
echo "Step 2: Creating Certificate..."
openssl req \
  -new \
  -x509 \
  -key $CERT_DIR/private.key \
  -config openssl.cnf \
  -days 365 \
  -extensions v3_req \
  -out $CERT_DIR/certificate.crt > /dev/null
echo "Step 2: Completed."
# --8<-- [end:create-certificate]


# --8<-- [start:combine]
echo "Step 3: Combining Private Key and Certificate..."
cat $CERT_DIR/private.key $CERT_DIR/certificate.crt > $CERT_DIR/trino-dev.pem
rm -f $CERT_DIR/private.key $CERT_DIR/certificate.crt
echo "Step 3: Completed."
# --8<-- [end:combine]


# --8<-- [start:create-k8s-secret]
echo "Step 4: Creating Kubernetes secret..."
kubectl create secret generic trino-tls-secret \
    --from-file=trino-dev.pem="$CERT_DIR/trino-dev.pem" \
    --dry-run=client -o yaml > "./trino-tls-secret.yaml"
echo "Step 4: Completed."
# --8<-- [end:create-k8s-secret]


echo "Certificate generation completed successfully!"
echo ""
echo "Generated files:"
echo "  - $CERT_DIR/trino-dev.pem (with private key and certificate)"
echo "  - trino-tls-secret.yaml (Kubernetes secret manifest)"