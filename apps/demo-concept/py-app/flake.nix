{
  description = "Python 3.13 application with uv";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python313
            uv
          ];

          shellHook = ''
            if [ ! -d .venv ]; then
              echo "Creating virtual environment..."
              uv venv
            fi
            source .venv/bin/activate
            echo "Python 3.13 environment with uv loaded."
            uv --version
            python3.13 --version
          '';
        };
      }
    );
}
