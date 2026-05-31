{ pkgs }:
let
  base = import ./base.nix { inherit pkgs; };
in
pkgs.mkShell {
  packages = base.packages ++ (with pkgs; [
    rustc
    cargo
    rustfmt
    clippy
    cargo-tarpaulin
  ]);

  shellHook = base.shellHook + ''
    if [ -z "$_RUST_SHELL_LOADED" ]; then
      export _RUST_SHELL_LOADED=1
    fi
  '';
}
