{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    nodejs_22      # Node LTS
    pnpm
  ]);

  shellHook = base.shellHook + ''
    echo "Node $(node --version)"
    echo "pnpm $(pnpm --version)"
  '';
}
