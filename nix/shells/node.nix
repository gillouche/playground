{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    nodejs_22
    pnpm
    nodePackages.typescript
    nodePackages.typescript-language-server
  ]);

  shellHook = base.shellHook + ''
    echo "Node $(node --version)"
    echo "pnpm $(pnpm --version)"
  '';
}
