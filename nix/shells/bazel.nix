{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    bazel_8
    go-containerregistry
    (python312.withPackages (ps: [ ps.pyyaml ]))
  ]);

  shellHook = base.shellHook + ''
    echo "Bazel $(bazel --version)"
    echo "Python $(python --version) with pyyaml"
    echo ""
    echo "Use 'bazel' commands for builds"
  '';
}
