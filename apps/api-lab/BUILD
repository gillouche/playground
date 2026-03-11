load("//tools:python_defs.bzl", "deploy_sandbox_all")

deploy_sandbox_all(
    name = "deploy_sandbox",
    app = "api-lab",
    components = [
        "//apps/api-lab/python-api:deploy_sandbox",
        "//apps/api-lab/go-api:deploy_sandbox",
        "//apps/api-lab/ts-api:deploy_sandbox",
        "//apps/api-lab/rust-traffic-generator:deploy_sandbox",
    ],
)
