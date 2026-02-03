# Local Development

## 1. Enter Shell
Always work inside the Nix shell to get correct tools.
```bash
use flake ./nix#bazel
```

## 2. Run Tests
Fast feedback loop.
```bash
bazel test //apps/demo-app/...
```

## 3. Build & Run Locally
To run a binary directly:
```bash
bazel run //apps/demo-app/greeting-service:main
```

## 4. Deploy to Minikube (Optional)
If you need to test k8s manifests locally.
```bash
bazel run //apps/demo-app:deploy_minikube
```
*   Builds images.
*   Loads them into Minikube docker daemon.
*   Applies Dev manifests to Minikube.
