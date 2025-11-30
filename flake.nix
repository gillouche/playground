{
  description = "Monorepo dev environment with Bazel, Nix, and Kubernetes tooling";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05"; # stable channel
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          # optionally avoid broken packages, reproducibility flags…
        };
      in {
        devShells.default = pkgs.mkShell {
          name = "dev-shell";

          buildInputs = [
            pkgs.bazel_7
            pkgs.kubectl
            pkgs.kustomize
            pkgs.helm    
            pkgs.jq
          ];

          shellHook = ''
            echo "Dev environment loaded with Bazel"
          '';
        };
      });
}
