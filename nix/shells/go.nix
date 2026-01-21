{ pkgs }:

pkgs.mkShell {
  packages = with pkgs; [
    go_1_23        # Latest Go supported by Bazel
    git
  ];

  shellHook = ''
    echo "Go $(go version)"
  '';
}
