load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_push", "oci_load")

def application(
    name,
    language,
    srcs = [],
    unit_tests = [],
    integration_tests = [],
    lint_cmd = None,
    test_cmd = None,
    build_cmd = None,
    image_repository = "",
    base_image = "@python_base"):
    
    defaults = {
        "python": {
            "lint": "uv sync --group dev && uv run ruff check .",
            "test": "uv sync --group dev && uv run pytest",
            "coverage": "uv sync --group dev && uv run pytest --cov=. --cov-fail-under=80",
            "build": "uv sync",
        },
        "rust": {
            "lint": "cargo clippy",
            "test": "cargo test",
            "coverage": "cargo tarpaulin --fail-under 80",
            "build": "cargo build --release",
        },
        "go": {
            "lint": "golangci-lint run",
            "test": "go test ./...",
            "coverage": "$BUILD_WORKSPACE_DIRECTORY/tools/scripts/check_go_coverage.sh .",
            "build": "go build -o bin/app",
        },
        "typescript": {
            "lint": "npm run lint",
            "test": "npm test",
            "coverage": "npm run coverage",
            "build": "npm run build",
        },
    }
    
    lang_defaults = defaults.get(language, {})
    lint_cmd = lint_cmd or lang_defaults.get("lint", "echo 'No lint configured'")
    test_cmd = test_cmd or lang_defaults.get("test", "echo 'No tests configured'")
    build_cmd = build_cmd or lang_defaults.get("build", "echo 'No build configured'")

    # Coverage command defaults
    coverage_cmd = lang_defaults.get("coverage", "echo 'No coverage configured'")
    
    # Create wrapper scripts for each command
    package_dir = native.package_name()
    
    # Lint target
    native.sh_binary(
        name = "lint",
        srcs = ["//tools/scripts/shell:run_command.sh"],
        args = [package_dir, lint_cmd],
        tags = ["lint"],
    )
    
    # Unit Test Target
    if unit_tests:
        # Construct unit test command (default for Python)
        unit_cmd = test_cmd
        unit_cov_cmd = coverage_cmd
        
        if language == "python":
            unit_cmd = "uv sync --group dev && uv run pytest tests/unit"
            unit_cov_cmd = "uv sync --group dev && uv run pytest --cov=. --cov-fail-under=80 tests/unit"
            
        native.sh_binary(
            name = "unit_test",
            srcs = ["//tools/scripts/shell:run_command.sh"],
            args = [package_dir, unit_cov_cmd],
            tags = ["test", "unit"],
        )
        
    # Integration Test Target
    if integration_tests:
         # Construct integration test command (default for Python)
        int_cmd = test_cmd
        int_cov_cmd = coverage_cmd
        
        if language == "python":
            int_cmd = "uv sync --group dev && uv run pytest tests/integration"
            int_cov_cmd = "uv sync --group dev && uv run pytest --cov=. --cov-fail-under=80 tests/integration"
            
        native.sh_binary(
            name = "integration_test",
            srcs = ["//tools/scripts/shell:run_command.sh"],
            args = [package_dir, int_cov_cmd],
            tags = ["test", "integration"],
        )
    
    # Build target
    native.sh_binary(
        name = "build",
        srcs = ["//tools/scripts/shell:run_command.sh"],
        args = [package_dir, build_cmd],
    )
    
    # Infer repository and concept from package path
    concept = "unknown"
    pkg_path = native.package_name()
    if pkg_path.startswith("apps/"):
        # Strip "apps/" prefix to get "concept/app"
        repo_suffix = pkg_path[len("apps/"):]
        parts = repo_suffix.split("/")
        if len(parts) >= 1:
            concept = parts[0]
            
        if not image_repository:
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
            srcs = ["//tools/scripts/shell:smart_push.sh"],
            data = [":_push_image_oci"],
            args = ["$(location :_push_image_oci)"],
        )
        
        # Load image into local docker daemon
        oci_load(
            name = "build_docker",
            image = ":image",
            repo_tags = ["{}:latest".format(name)],
        )

        # Sandbox deployment target for minikube
        native.sh_binary(
            name = "_deploy_minikube",
            srcs = ["//tools/scripts/shell:deploy_minikube.sh"],
            args = [package_dir, image_repository, name],
            data = native.glob(["deploy/**/*"], allow_empty=True),
        )
        
        # Combined sandbox target: load image + deploy to minikube
        native.sh_binary(
            name = "deploy_sandbox",
            srcs = ["//tools/scripts/shell:sandbox_workflow.sh"],
            args = [name, "//" + package_dir + ":_deploy_minikube", package_dir],
        )

        # Dev Deployment
        native.sh_binary(
            name = "deploy_dev",
            srcs = ["//tools/scripts/shell:run_command.sh"],
            args = [package_dir, "bazelisk run //tools:sync_dev -- --app " + concept + " --component " + name], 
        )

        # Test Deployment
        native.sh_binary(
            name = "deploy_test",
            srcs = ["//tools/scripts/shell:run_command.sh"],
            args = [package_dir, "echo 'Not implemented yet'"], 
        )

        # Prod Deployment
        native.sh_binary(
            name = "deploy_prod",
            srcs = ["//tools/scripts/shell:run_command.sh"],
            args = [package_dir, "echo 'Not implemented yet'"], 
        )

