{ pkgs }:

let
  python = import ./python.nix { inherit pkgs; };
  rust = import ./rust.nix { inherit pkgs; };
  node = import ./node.nix { inherit pkgs; };
  go = import ./go.nix { inherit pkgs; };
in
pkgs.mkShell {
  # Inherit all packages and environment variables from other shells
  inputsFrom = [
    python
    rust
    node
    go
  ];

  packages = with pkgs; [
    trivy
    crane  # OCI registry tool for digest queries (smart push)
    skopeo # Alternative OCI tool for registry operations
    sonar-scanner-cli  # SonarQube analysis
    jdk    # For keytool (Java truststore management for Bazel oci.pull)
  ];

  shellHook = ''
    echo "🛠️  CI Shell Activated (Composed)"
    echo "Bazel: $(bazel --version)"
    echo "Python: $(python --version)"
    echo "UV: $(uv --version)"
    echo "Go: $(go version)"
    echo "Node: $(node --version)"

    # Configure custom CA bundle for SSL
    export PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    export CA_BUNDLE="$PROJECT_ROOT/ca-bundle.pem"

    if [ -f "$CA_BUNDLE" ]; then
      echo "🔒 Found custom CA bundle: $CA_BUNDLE"
      export NODE_EXTRA_CA_CERTS="$CA_BUNDLE"
      export SSL_CERT_FILE="$CA_BUNDLE"
      export REQUESTS_CA_BUNDLE="$CA_BUNDLE"

      # Create Java truststore for Bazel's JVM so oci.pull can access the private Nexus registry.
      # Bazel's embedded JVM does not honor SSL_CERT_FILE; it needs a JKS truststore.
      BAZEL_TRUSTSTORE="/tmp/bazel-ssl-truststore"
      if [ ! -f "$BAZEL_TRUSTSTORE" ]; then
        JAVA_CACERTS="$(dirname "$(dirname "$(readlink -f "$(which java)")")")/lib/security/cacerts"
        if [ -f "$JAVA_CACERTS" ]; then
          cp "$JAVA_CACERTS" "$BAZEL_TRUSTSTORE"
          # Extract the Homelab Root CA (first cert in the bundle) and import it
          awk '/-----BEGIN CERTIFICATE-----/{n++} n==1{print} /-----END CERTIFICATE-----/ && n==1{exit}' "$CA_BUNDLE" > /tmp/homelab-root-ca.pem
          keytool -importcert -keystore "$BAZEL_TRUSTSTORE" -storepass changeit \
            -noprompt -alias "homelab-root-ca" -file /tmp/homelab-root-ca.pem 2>/dev/null || true
          rm -f /tmp/homelab-root-ca.pem
          echo "Java truststore created with Homelab Root CA"
        fi
      fi
      if [ -f "$BAZEL_TRUSTSTORE" ]; then
        export JAVA_TOOL_OPTIONS="-Djavax.net.ssl.trustStore=$BAZEL_TRUSTSTORE -Djavax.net.ssl.trustStorePassword=changeit"
      fi
    else
      echo "CA bundle not found at $CA_BUNDLE"
    fi
  '';
}
