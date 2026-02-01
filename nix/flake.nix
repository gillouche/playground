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
          # Bazel shell: Bazel 7.x (default for root)
          bazel = import ./shells/bazel.nix { inherit pkgs; };
          
          # Base shell: Common tools (git, ytt, etc)
          base = pkgs.mkShell (import ./shells/base.nix { inherit pkgs; });
          
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

          # Default: Bazel (for root development)
          default = self.devShells.${system}.bazel;
        }
      );
    };
}
