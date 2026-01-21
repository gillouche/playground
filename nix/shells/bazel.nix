{ pkgs }:

pkgs.mkShell {
  packages = with pkgs; [
    bazelisk
    git
  ];

  shellHook = ''
    echo "Bazelisk $(bazelisk --version)"
    echo ""
    echo "Use 'bazelisk' commands for builds"
  '';
}
