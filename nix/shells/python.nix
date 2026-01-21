{ pkgs }:

pkgs.mkShell {
  packages = with pkgs; [
    python313      # Latest Python 3.13
    uv             # UV package manager
    git
  ];

  shellHook = ''
    echo "Python version -> $(python --version)"
    echo "uv version -> $(uv --version)"
    echo ""
    echo "Run 'uv sync --all-extras' to install project dependencies"
  '';
}
