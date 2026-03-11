{ pkgs }:

{
  packages = with pkgs; [
    git
    ytt
    curl
    jq
    kubectl
    kustomize
    # Bazel tools (from merged bazel.nix)
    bazel_8
    go-containerregistry
    (python314.withPackages (ps: [ ps.pyyaml ]))
  ];

  shellHook = ''
    if [ -z "$_BASE_SHELL_LOADED" ]; then
      export _BASE_SHELL_LOADED=1
    fi
  '';
}
