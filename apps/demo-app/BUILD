load("//tools:python_defs.bzl", "deploy_sandbox_all")

deploy_sandbox_all(
    name = "deploy_sandbox",
    app = "demo-app",
    components = [
        "//apps/demo-app/greeting-service:deploy_sandbox",
        "//apps/demo-app/infra-check-service:deploy_sandbox",
        "//apps/demo-app/traffic-generator-service:deploy_sandbox",
    ],
)
