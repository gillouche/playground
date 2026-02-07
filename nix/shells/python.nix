{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    uv
  ]);

  shellHook = base.shellHook + ''
    echo "Python version -> $(python --version)"
    echo "uv version -> $(uv --version)"
    echo ""
    echo "Run 'uv sync --all-extras' to install project dependencies"

    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
  '';
}
