{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    go
    gopls
    gotools  # goimports, etc.
    golangci-lint
  ]);

  shellHook = base.shellHook + ''
    if [ -z "$_GO_SHELL_LOADED" ]; then
      export _GO_SHELL_LOADED=1
    fi
  '';
}
