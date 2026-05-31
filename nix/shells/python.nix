{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    uv
  ]);

  shellHook = base.shellHook + ''
    if [ -z "$_PYTHON_SHELL_LOADED" ]; then
      export _PYTHON_SHELL_LOADED=1
      export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    fi
  '';
}
