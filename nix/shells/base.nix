{ pkgs }:

{
  packages = with pkgs; [
    git
    ytt
    curl
    jq
    kubectl
    kustomize
    # Bazel tools (from merged bazel.nix)
    bazel_8
    go-containerregistry
    (python314.withPackages (ps: [ ps.pyyaml ]))
  ];

  shellHook = ''
    echo "🛠️  Base Shell Tools Loaded (git, ytt, curl, jq, bazel, python)"
    echo "Bazel: $(bazel --version)"
    echo "Python: $(python --version)"
  '';
}
