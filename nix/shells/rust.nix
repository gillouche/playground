{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    rustc
    cargo
    cargo-tarpaulin
  ]);

  shellHook = base.shellHook + ''
    echo "Rust $(rustc --version)"
    echo "Cargo $(cargo --version)"
  '';
}
