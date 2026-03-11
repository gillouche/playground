{
  description = "Playground monorepo toolchains";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      # Support both macOS M4 and Arch Linux AMD
      systems = [ "aarch64-darwin" "x86_64-linux" ];

      forAllSystems = nixpkgs.lib.genAttrs systems;

      pkgsFor = system: import nixpkgs { inherit system; };
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = pkgsFor system;
        in
        {
          # Bazel shell: Now merged into base
          # base = ... (already defined below)

          # Base shell: Common tools (git, ytt, curl, jq, kubectl, kustomize, bazel, python)
          base = pkgs.mkShell (import ./shells/base.nix { inherit pkgs; });

          # Use base as the bazel shell alias
          bazel = self.devShells.${system}.base;

          # Python shell: Python 3.12 + uv
          python = import ./shells/python.nix { inherit pkgs; };

          # Rust shell: Latest stable + cargo
          rust = import ./shells/rust.nix { inherit pkgs; };

          # Go shell: Latest supported by Bazel
          go = import ./shells/go.nix { inherit pkgs; };

          # Node shell: LTS + pnpm
          node = import ./shells/node.nix { inherit pkgs; };

          # CI shell: All tools for CI
          ci = import ./shells/ci.nix { inherit pkgs; };

          # Default: All toolchains + pre-commit (so all pre-commit hooks work)
          # shellHook prepends python314 to PATH so it takes priority over pre-commit's python
          default = let
            python314Env = pkgs.python314.withPackages (ps: [ ps.pyyaml ]);
          in pkgs.mkShell {
            inputsFrom = [
              self.devShells.${system}.go
              self.devShells.${system}.node
              self.devShells.${system}.rust
            ];
            packages = [
              pkgs.pre-commit
              python314Env
              pkgs.uv
              pkgs.jdk  # keytool for Java truststore creation
            ];
            shellHook = ''
              export PATH="${python314Env}/bin:$PATH"

              # Configure CA bundle for internal Nexus proxy (homelab root CA)
              PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
              CA_BUNDLE="$PROJECT_ROOT/ca-bundle.pem"
              ROOT_CA="$PROJECT_ROOT/homelab-root-ca.crt"
              if [ -f "$CA_BUNDLE" ]; then
                export SSL_CERT_FILE="$CA_BUNDLE"
                export REQUESTS_CA_BUNDLE="$CA_BUNDLE"
                export NODE_EXTRA_CA_CERTS="$CA_BUNDLE"
              fi

              # Create Java truststore for Bazel's JVM: system CAs + homelab root CA
              if [ -f "$ROOT_CA" ]; then
                TRUSTSTORE="$PROJECT_ROOT/.truststore.jks"
                if [ ! -f "$TRUSTSTORE" ] || [ "$ROOT_CA" -nt "$TRUSTSTORE" ]; then
                  rm -f "$TRUSTSTORE"
                  # Start from the JDK's default cacerts (includes public CAs)
                  JAVA_CACERTS="$(dirname "$(dirname "$(readlink -f "$(which java)")")")/lib/security/cacerts"
                  if [ -f "$JAVA_CACERTS" ]; then
                    cp "$JAVA_CACERTS" "$TRUSTSTORE"
                    chmod u+w "$TRUSTSTORE"
                  fi
                  # Add the homelab root CA
                  keytool -importcert -noprompt -trustcacerts \
                    -alias "homelab-root-ca" \
                    -file "$ROOT_CA" \
                    -keystore "$TRUSTSTORE" \
                    -storepass changeit 2>/dev/null || true
                fi
                if [ -f "$TRUSTSTORE" ]; then
                  cat > "$PROJECT_ROOT/.bazelrc.ci" << EOF
startup --host_jvm_args=-Djavax.net.ssl.trustStore=$TRUSTSTORE
startup --host_jvm_args=-Djavax.net.ssl.trustStorePassword=changeit
EOF
                fi
              elif [ -f /etc/ssl/certs/java/cacerts ]; then
                cat > "$PROJECT_ROOT/.bazelrc.ci" << 'CIEOF'
startup --host_jvm_args=-Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts
startup --host_jvm_args=-Djavax.net.ssl.trustStorePassword=changeit
CIEOF
              fi

              echo "Dev shell loaded: Python $(python --version 2>&1 | cut -d' ' -f2), Go $(go version 2>&1 | cut -d' ' -f3), Node $(node --version), Rust $(rustc --version 2>&1 | cut -d' ' -f2), Bazel $(bazel --version 2>&1 | head -1 | cut -d' ' -f2)"
            '';
          };
        }
      );

      packages = forAllSystems (system:
        {
          ci = self.devShells.${system}.ci;
          default = self.devShells.${system}.ci;
        }
      );
    };
}
