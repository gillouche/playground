{
  description = "Monorepo dev environment with Bazel, Nix, and Kubernetes tooling";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          name = "dev-shell";

          buildInputs = [
            pkgs.bazelisk
          ];

          shellHook = ''
            echo "Dev environment loaded with Bazelisk"
          '';
        };
      });
}
