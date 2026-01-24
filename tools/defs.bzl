load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_push", "oci_load")

def application(
    name,
    language,
    srcs = [],
    tests = [],
    lint_cmd = None,
    test_cmd = None,
    build_cmd = None,
    image_repository = "",
    base_image = "@python_base"):
    """
    Generic application builder for monorepo.
    
    Creates consistent targets across languages:
      - :lint - Runs linting
      - :test - Runs tests  
      - :build - Builds artifacts
      - :image - Creates OCI image
      - :image_tarball - Creates Tarball for localdev
      - :push_image - Pushes to registry
      - :load_image - Loads image into local docker (replaces old build_docker)
    
    Args:
        name: Application name
        language: python|rust|go|typescript
        srcs: Source files
        tests: Test files
        lint_cmd: Command to run linting (defaults based on language)
        test_cmd: Command to run tests (defaults based on language)
        build_cmd: Command to build (defaults based on language)
        image_repository: Docker registry URL
        base_image: Base OCI image
    """
    
    # Language-specific defaults
    defaults = {
        "python": {
            "lint": "uv sync --group dev && uv run ruff check .",
            "test": "uv sync --group dev && uv run pytest",
            "build": "uv sync",
        },
        "rust": {
            "lint": "cargo clippy",
            "test": "cargo test",
            "build": "cargo build --release",
        },
        "go": {
            "lint": "golangci-lint run",
            "test": "go test ./...",
            "build": "go build -o bin/app",
        },
        "typescript": {
            "lint": "npm run lint",
            "test": "npm test",
            "build": "npm run build",
        },
    }
    
    lang_defaults = defaults.get(language, {})
    lint_cmd = lint_cmd or lang_defaults.get("lint", "echo 'No lint configured'")
    test_cmd = test_cmd or lang_defaults.get("test", "echo 'No tests configured'")
    build_cmd = build_cmd or lang_defaults.get("build", "echo 'No build configured'")
    
    # Create wrapper scripts for each command
    package_dir = native.package_name()
    
    # Lint target
    native.sh_binary(
        name = "lint",
        srcs = ["//tools/scripts:run_command.sh"],
        args = [package_dir, lint_cmd],
        tags = ["lint"],
    )
    
    # Test target  
    native.sh_binary(
        name = "test",
        srcs = ["//tools/scripts:run_command.sh"],
        args = [package_dir, test_cmd],
        tags = ["test"],
    )
    
    # Build target
    native.sh_binary(
        name = "build",
        srcs = ["//tools/scripts:run_command.sh"],
        args = [package_dir, build_cmd],
    )
    
    # OCI Image
    # Infer repository from package path if not provided
    if not image_repository:
        pkg_path = native.package_name()
        if pkg_path.startswith("apps/"):
            # Strip "apps/" prefix to get "concept/app"
            repo_suffix = pkg_path[len("apps/"):]
            image_repository = "nexus.gillouche.homelab/docker-hosted/{}".format(repo_suffix)
            
    if image_repository:
        # 1. Create a requirements.txt from pyproject.toml / uv.lock
        native.genrule(
            name = "gen_requirements",
            srcs = ["pyproject.toml", "uv.lock"],
            outs = ["requirements.txt"],
            cmd = "uv export --project $$(dirname $(location pyproject.toml)) --format requirements-txt --no-dev --frozen > $@",
        )

        # 2. Install dependencies using uv for ARM64
        native.genrule(
            name = "install_deps",
            srcs = ["requirements.txt"],
            outs = ["deps.tar"],
            cmd = """
                mkdir -p tmp/app/site-packages
                uv pip install -r $(location requirements.txt) \\
                    --target tmp/app/site-packages \\
                    --system \\
                    --python-version 3.13 \\
                    --python-platform aarch64-unknown-linux-musl
                # Set deterministic timestamps and ownership
                find tmp/app -exec touch -t 197001010000 {} +
                tar --owner=0 --group=0 --mode=0755 -cf $@ -C tmp .
            """,
        )

        # 3. Wrap the tarball (mainly to be a valid target for oci_image provided tars)
        pkg_tar(
            name = "deps_layer",
            deps = [":install_deps"],
        )

        pkg_tar(
            name = "app_layer",
            srcs = srcs,
            package_dir = "/app",
            mode = "0755",
        )
        
        oci_image(
            name = "image",
            base = "@python_base_linux_arm64_v8",
            tars = [
                ":deps_layer",
                ":app_layer"
            ],
            env = {
                 "PYTHONPATH": "/app/site-packages",
            },
        )
        
        oci_push(
            name = "_push_image_oci",
            image = ":image",
            repository = image_repository,
            # No static tags here; they are passed by the wrapper
        )
        
        # Wrapper script to apply dynamic git tags at runtime
        native.sh_binary(
            name = "push_image",
            srcs = ["//tools/scripts:smart_push.sh"],
            data = [":_push_image_oci"],
            args = ["$(location :_push_image_oci)"],
        )
        
        # Load image into local docker daemon
        # Replaces old 'build_docker' ensuring local parity with prod
        oci_load(
            name = "build_docker",
            image = ":image",
            repo_tags = ["{}:latest".format(name)],
        )

        # Sandbox deployment target for minikube
        native.sh_binary(
            name = "deploy_sandbox",
            srcs = ["//tools/scripts:deploy_minikube.sh"],
            args = [package_dir, image_repository, name],
            data = native.glob(["deploy/**/*"], allow_empty=True),
        )
        
        # Combined sandbox target: load image + deploy to minikube
        native.sh_binary(
            name = "build_sandbox",
            srcs = ["//tools/scripts:sandbox_workflow.sh"],
            args = [name, "//" + package_dir + ":deploy_sandbox", package_dir],
        )

