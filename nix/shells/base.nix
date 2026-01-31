{ pkgs }:

{
  packages = with pkgs; [
    git
    ytt
    curl
    jq
    kubectl
    kustomize
  ];

  shellHook = ''
    echo "🛠️  Base Shell Tools Loaded (git, ytt, curl, jq)"
  '';
}
