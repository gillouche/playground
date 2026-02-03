load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", pkg_strip_prefix = "strip_prefix")
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
    base_image = "@python_base_linux_arm64_v8",
    coverage_threshold = 80,
    visibility = ["//visibility:public"]):
    
    defaults = {
        "python": {
            "lint": "uv sync --group dev && uv run ruff check .",
            "test": "uv sync --group dev && uv run pytest",
            "coverage": "uv sync --group dev && uv run pytest --cov=. --cov-fail-under={}".format(coverage_threshold),
            "build": "uv sync",
        },
        "rust": {
            "lint": "cargo clippy",
            "test": "cargo test",
            "coverage": "cargo tarpaulin --fail-under {}".format(coverage_threshold),
            "build": "cargo build --release",
        },
        "go": {
            "lint": "golangci-lint run",
            "test": "go test ./...",
            "coverage": "$BUILD_WORKSPACE_DIRECTORY/tools/ci/check_go_coverage.sh . {}".format(coverage_threshold),
            "build": "go build -o bin/app",
        },
        "typescript": {
            "lint": "npm run lint",
            "test": "npm test",
            "coverage": "npm run coverage -- --coverage-threshold {}".format(coverage_threshold),
            "build": "npm run build",
        },
    }
    
    lang_defaults = defaults.get(language, {})
    lint_cmd = lint_cmd or lang_defaults.get("lint", "echo 'No lint configured'")
    test_cmd = test_cmd or lang_defaults.get("test", "echo 'No tests configured'")
    build_cmd = build_cmd or lang_defaults.get("build", "echo 'No build configured'")

    # Coverage command defaults
    coverage_cmd = lang_defaults.get("coverage", "echo 'No coverage configured'")
    
    if language == "python":
        ssl_init = "if [ -f \"$$BUILD_WORKSPACE_DIRECTORY/ca-bundle.pem\" ]; then export SSL_CERT_FILE=\"$$BUILD_WORKSPACE_DIRECTORY/ca-bundle.pem\"; fi && "
        if not lint_cmd.startswith("echo"):
            lint_cmd = ssl_init + "unset VIRTUAL_ENV && " + lint_cmd
        if not build_cmd.startswith("echo"):
            build_cmd = ssl_init + build_cmd
        if not coverage_cmd.startswith("echo"):
            coverage_cmd = ssl_init + coverage_cmd
    
    # Create wrapper scripts for each command
    package_dir = native.package_name()
    
    # Lint target
    native.sh_binary(
        name = "lint",
        srcs = ["//tools/dev:run_command.sh"],
        args = [package_dir, lint_cmd],
        data = srcs + unit_tests + integration_tests,
        tags = ["lint"],
        visibility = visibility,
    )
    
    # Unit Test Target
    if unit_tests:
        # Construct unit test command (default for Python)
        unit_cmd = test_cmd
        unit_cov_cmd = coverage_cmd
        
        if language == "python":
            ssl_init = "if [ -f \"$$BUILD_WORKSPACE_DIRECTORY/ca-bundle.pem\" ]; then export SSL_CERT_FILE=\"$$BUILD_WORKSPACE_DIRECTORY/ca-bundle.pem\"; fi && "
            unit_cmd = ssl_init + "unset VIRTUAL_ENV && uv sync --group dev && uv run pytest tests/unit"
            unit_cov_cmd = ssl_init + "unset VIRTUAL_ENV && uv sync --group dev && uv run pytest --cov=. --cov-fail-under={} tests/unit".format(coverage_threshold)
            
        native.sh_binary(
            name = "unit_test",
            srcs = ["//tools/dev:run_command.sh"],
            args = [package_dir, unit_cov_cmd],
            data = unit_tests + srcs,
            tags = ["test", "unit"],
            visibility = visibility,
        )
        
    # Integration Test Target
    if integration_tests:
         # Construct integration test command (default for Python)
        int_cmd = test_cmd
        int_cov_cmd = coverage_cmd
        
        if language == "python":
            ssl_init = "if [ -f \"$$BUILD_WORKSPACE_DIRECTORY/ca-bundle.pem\" ]; then export SSL_CERT_FILE=\"$$BUILD_WORKSPACE_DIRECTORY/ca-bundle.pem\"; fi && "
            int_cmd = ssl_init + "unset VIRTUAL_ENV && uv sync --group dev && uv run pytest tests/integration"
            int_cov_cmd = ssl_init + "unset VIRTUAL_ENV && uv sync --group dev && uv run pytest --cov=. --cov-fail-under={} tests/integration".format(coverage_threshold)
            
        native.sh_binary(
            name = "integration_test",
            srcs = ["//tools/dev:run_command.sh"],
            args = [package_dir, int_cov_cmd],
            data = integration_tests + srcs,
            tags = ["test", "integration"],
            visibility = visibility,
        )
    
    # Build target
    native.sh_binary(
        name = "build",
        srcs = ["//tools/dev:run_command.sh"],
        args = [package_dir, build_cmd],
        visibility = visibility,
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
            srcs = [
                "requirements.txt",
                "//tools/deploy:install_python_deps.sh",
            ],
            outs = ["deps.tar"],
            cmd = "bash $(location //tools/deploy:install_python_deps.sh) $(location requirements.txt) $@",
        )

        # 3. Wrap the tarball (mainly to be a valid target for oci_image provided tars)
        pkg_tar(
            name = "deps_layer",
            deps = [":install_deps"],
        )

        # Manual tar packing to ensure correct structure (src/... -> /app/src/...)
        native.genrule(
            name = "app_layer_tar",
            srcs = srcs + ["//tools/deploy:package_app.py"],
            outs = ["app_layer.tar"],
            cmd = "python3 $(location //tools/deploy:package_app.py) $@ $(SRCS)",
        )
        
        oci_image(
            name = "image",
            base = base_image,
            tars = [
                ":deps_layer",
                ":app_layer_tar"
            ],
            env = {
                 "PYTHONPATH": "/app/src:/app/site-packages",
            },
            labels = {
                "org.opencontainers.image.source": "https://github.com/gillouche/playground",
                "org.opencontainers.image.title": name,
                "org.opencontainers.image.description": "{} container image".format(name),
            },
            visibility = visibility,
        )
        
        oci_push(
            name = "_push_image_oci",
            image = ":image",
            repository = image_repository,
            # No static tags here; they are passed by the wrapper
            visibility = ["//visibility:private"],
        )

        oci_push(
            name = "push_oci",
            image = ":image",
            repository = image_repository,
            visibility = visibility,
        )

        # Wrapper script to apply dynamic git tags at runtime
        native.sh_binary(
            name = "push_image",
            srcs = ["//tools/ci:smart_push.sh"],
            data = [":_push_image_oci", "//tools/ci:determine_base_commit"],
            args = ["$(location :_push_image_oci)"],
            visibility = visibility,
        )

        # Load image into local docker daemon
        oci_load(
            name = "build_docker",
            image = ":image",
            repo_tags = ["{}:latest".format(name)],
            visibility = visibility,
        )

        # Sandbox deployment target for minikube
        native.sh_binary(
            name = "_deploy_minikube",
            srcs = ["//tools/deploy:deploy_minikube.sh"],
            args = [package_dir, image_repository, name],
            data = native.glob(["deploy/**/*"], allow_empty=True),
            visibility = ["//visibility:private"],
        )

        # Combined sandbox target: load image + deploy to minikube
        native.sh_binary(
            name = "deploy_sandbox",
            srcs = ["//tools/deploy:sandbox_workflow.sh"],
            args = [name, "//" + package_dir + ":_deploy_minikube", package_dir],
            visibility = visibility,
        )

        # Dev Deployment
        native.sh_binary(
            name = "deploy_dev",
            srcs = ["//tools/dev:run_command.sh"],
            args = [package_dir, "bazel run //tools:sync_dev -- --app " + concept + " --component " + name],
            visibility = visibility,
        )

        # Test Deployment
        native.sh_binary(
            name = "deploy_test",
            srcs = ["//tools/dev:run_command.sh"],
            args = [package_dir, "echo 'Not implemented yet'"],
            visibility = visibility,
        )

        # Prod Deployment
        native.sh_binary(
            name = "deploy_prod",
            srcs = ["//tools/dev:run_command.sh"],
            args = [package_dir, "echo 'Not implemented yet'"],
            visibility = visibility,
        )


def deploy_sandbox_all(name, app, components = []):
    native.sh_binary(
        name = name,
        srcs = ["//tools/deploy:deploy_sandbox_all.sh"],
        args = [app],
    )
