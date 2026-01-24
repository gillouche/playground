{ pkgs }:

{
  packages = with pkgs; [
    git
    ytt
    curl
    jq
    kubectl
  ];

  shellHook = ''
    echo "🛠️  Base Shell Tools Loaded (git, ytt, curl, jq)"
  '';
}
