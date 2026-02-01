{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    python312
    uv
  ]);

  shellHook = base.shellHook + ''
    echo "Python version -> $(python --version)"
    echo "uv version -> $(uv --version)"
    echo ""
    echo "Run 'uv sync --all-extras' to install project dependencies"
  '';
}
