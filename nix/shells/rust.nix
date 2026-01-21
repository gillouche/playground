{ pkgs }:

pkgs.mkShell {
  packages = with pkgs; [
    rustc          # Latest stable Rust
    cargo
    rustfmt
    clippy
    git
  ];

  shellHook = ''
    echo "Rust $(rustc --version)"
    echo "Cargo $(cargo --version)"
  '';
}
