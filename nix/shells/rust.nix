{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    rustc          # Latest stable Rust
    cargo
    rustfmt
    clippy
  ]);

  shellHook = base.shellHook + ''
    echo "Rust $(rustc --version)"
    echo "Cargo $(cargo --version)"
  '';
}
