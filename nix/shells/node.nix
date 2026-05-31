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
    if [ -z "$_NODE_SHELL_LOADED" ]; then
      export _NODE_SHELL_LOADED=1
    fi
  '';
}
