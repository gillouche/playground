load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_push")

def application(
    name,
    language,
    srcs = [],
    tests = [],
    lint_cmd = None,
    test_cmd = None,
    build_cmd = None,
    image_repository = "",
    base_image = "@distroless_python"):
    """
    Generic application builder for monorepo.
    
    Creates consistent targets across languages:
      - :lint - Runs linting
      - :test - Runs tests  
      - :build - Builds artifacts
      - :image - Creates OCI image
      - :image_tarball - Creates Tarball for localdev
      - :push_image - Pushes to registry
    
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
        pkg_tar(
            name = "app_layer",
            srcs = srcs,
            package_dir = "/app",
        )
        
        oci_image(
            name = "image",
            base = base_image,
            tars = [":app_layer"],
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
        
        # Dev deployment target for minikube
        native.sh_binary(
            name = "deploy_dev",
            srcs = ["//tools/scripts:deploy_minikube.sh"],
            args = [package_dir, image_repository, name],
            data = native.glob(["deploy/**/*"], allow_empty=True),
        )
        
        # Combined dev target: build image + deploy to minikube
        # We pass 'name' as the IMAGE_TARGET arg so it builds py-app:latest
        native.sh_binary(
            name = "dev",
            srcs = ["//tools/scripts:dev_workflow.sh"],
            args = [name, "//" + package_dir + ":deploy_dev", package_dir],
        )
        
        # Build Docker image from Dockerfile (for local dev)
        native.sh_binary(
            name = "build_docker",
            srcs = ["//tools/scripts:build_docker.sh"],
            args = [package_dir, name],
            tags = ["manual"],
        )

