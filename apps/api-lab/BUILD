load("//tools:python_defs.bzl", "deploy_sandbox_all")

deploy_sandbox_all(
    name = "deploy_sandbox",
    app = "api-lab",
    components = [
        "//apps/api-lab/python-rest-api:deploy_sandbox",
        "//apps/api-lab/python-grpc-api:deploy_sandbox",
        "//apps/api-lab/graphql-gateway:deploy_sandbox",
        "//apps/api-lab/go-api:deploy_sandbox",
        "//apps/api-lab/ts-api:deploy_sandbox",
        "//apps/api-lab/rust-traffic-generator:deploy_sandbox",
    ],
)

# Export lockfiles for MODULE.bazel pip.parse
exports_files([
    "requirements.in",
    "requirements_lock.txt",
    "requirements_dev.in",
    "requirements_dev_lock.txt",
])
