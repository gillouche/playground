{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    go
    gopls
    gotools  # goimports, etc.
  ]);

  shellHook = base.shellHook + ''
    echo "Go $(go version)"
  '';
}
