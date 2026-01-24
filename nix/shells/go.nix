{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    go_1_24        # Latest Go supported by Bazel
  ]);

  shellHook = base.shellHook + ''
    echo "Go $(go version)"
  '';
}
