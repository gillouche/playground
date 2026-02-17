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
    else
      echo "CA bundle not found at $CA_BUNDLE"
    fi
  '';
}
