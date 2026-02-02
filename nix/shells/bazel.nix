{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    bazel_8
  ]);

  shellHook = base.shellHook + ''
    echo "Bazel $(bazel --version)"
    echo ""
    echo "Use 'bazel' commands for builds"
  '';
}
