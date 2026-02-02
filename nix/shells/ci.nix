{ pkgs }:

let
  python = import ./python.nix { inherit pkgs; };
  rust = import ./rust.nix { inherit pkgs; };
  node = import ./node.nix { inherit pkgs; };
  go = import ./go.nix { inherit pkgs; };
  bazel = import ./bazel.nix { inherit pkgs; };
in
pkgs.mkShell {
  # Inherit all packages and environment variables from other shells
  inputsFrom = [
    python
    rust
    node
    go
    bazel
  ];

  packages = with pkgs; [
    go-containerregistry  # Provides 'crane' for efficient image operations
    trivy
    jq
  ];

  shellHook = ''
    echo "🛠️  CI Shell Activated (Composed)"
    echo "Bazel: $(bazel --version)"
    echo "Python: $(python --version)"
    echo "UV: $(uv --version)"
    echo "Go: $(go version)"
    echo "Node: $(node --version)"
  '';
}
