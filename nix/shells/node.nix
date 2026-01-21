{ pkgs }:

pkgs.mkShell {
  packages = with pkgs; [
    nodejs_22      # Node LTS
    pnpm
    git
  ];

  shellHook = ''
    echo "Node $(node --version)"
    echo "pnpm $(pnpm --version)"
  '';
}
