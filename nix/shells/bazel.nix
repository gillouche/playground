{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    bazelisk
  ]);

  shellHook = base.shellHook + ''
    echo "Bazelisk $(bazelisk --version)"
    echo ""
    echo "Use 'bazelisk' commands for builds"
  '';
}
