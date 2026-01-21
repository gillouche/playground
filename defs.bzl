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
    native.genrule(
        name = "_lint_script",
        outs = ["lint.sh"],
        cmd = """
cat > $@ <<'EOF'
#!/bin/bash
set -euo pipefail
cd "$$BUILD_WORKSPACE_DIRECTORY/{package}"
{cmd}
EOF
chmod +x $@
        """.format(package=package_dir, cmd=lint_cmd),
    )
    
    native.sh_binary(
        name = "lint",
        srcs = [":_lint_script"],
        tags = ["lint"],
    )
    
    # Test target  
    native.genrule(
        name = "_test_script",
        outs = ["test.sh"],
        cmd = """
cat > $@ <<'EOF'
#!/bin/bash
set -euo pipefail
cd "$$BUILD_WORKSPACE_DIRECTORY/{package}"
{cmd}
EOF
chmod +x $@
        """.format(package=package_dir, cmd=test_cmd),
    )
    
    native.sh_binary(
        name = "test",
        srcs = [":_test_script"],
        tags = ["test"],
    )
    
    # Build target
    native.genrule(
        name = "_build_script",
        outs = ["build.sh"],
        cmd = """
cat > $@ <<'EOF'
#!/bin/bash
set -euo pipefail
cd "$$BUILD_WORKSPACE_DIRECTORY/{package}"
{cmd}
EOF
chmod +x $@
        """.format(package=package_dir, cmd=build_cmd),
    )
    
    native.sh_binary(
        name = "build",
        srcs = [":_build_script"],
    )
    
    # OCI Image (if repository specified)
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
            name = "push_image",
            image = ":image",
            repository = image_repository,
            remote_tags = ["latest"],
        )
        
        # Dev deployment target for minikube
        native.genrule(
            name = "_deploy_dev_script",
            outs = ["deploy_dev.sh"],
            cmd = """
cat > $@ <<'EOF'
#!/bin/bash
set -euo pipefail

# Switch to minikube context
echo "Switching to minikube context..."
kubectl config use-context minikube

echo "Loading image to minikube..."
minikube image load {simple_name}:latest

echo "Deploying to minikube..."
DEPLOY_DIR="$$BUILD_WORKSPACE_DIRECTORY/{package}/deploy"

# Extract parent directory name (e.g., demo-concept from apps/demo-concept/py-app)
PARENT_DIR=$$(echo "{package}" | cut -d'/' -f2)
NAMESPACE="playground-$$PARENT_DIR-dev"

if [ -d "$$DEPLOY_DIR/dev" ]; then
  kubectl apply -k "$$DEPLOY_DIR/dev" -n "$$NAMESPACE"
elif [ -d "$$DEPLOY_DIR/base" ]; then
  kubectl create namespace "$$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply -k "$$DEPLOY_DIR/base" -n "$$NAMESPACE"
else
  echo "Error: No deploy directory found at $$DEPLOY_DIR"
  exit 1
fi

echo "Deployment complete to namespace: $$NAMESPACE"
EOF
chmod +x $@
            """.format(package=package_dir, repo=image_repository, simple_name=name),
        )
        
        native.sh_binary(
            name = "deploy_dev",
            srcs = [":_deploy_dev_script"],
            data = native.glob(["deploy/**/*"], allow_empty=True),
        )
        
        # Combined dev target: build image + deploy to minikube
        native.genrule(
            name = "_dev_script",
            outs = ["dev.sh"],
            cmd = """
cat > $@ <<'EOF'
#!/bin/bash
set -euo pipefail

cd "$$BUILD_WORKSPACE_DIRECTORY"

echo "Building OCI image..."
bazelisk build {image_target}

echo "Loading image to minikube..."
# Load the OCI tarball directly to minikube
minikube image load bazel-bin/{package}/image/tarball.tar --daemon

echo "Deploying to minikube..."
bazelisk run {deploy_target}
EOF
chmod +x $@
            """.format(
                image_target="//" + package_dir + ":image",
                deploy_target="//" + package_dir + ":deploy_dev",
                package=package_dir,
                repo=image_repository,
                simple_name=name,
            ),
        )
        
        native.sh_binary(
            name = "dev",
            srcs = [":_dev_script"],
        )

