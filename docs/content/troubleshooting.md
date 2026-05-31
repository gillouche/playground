# Troubleshooting

## Nix

### "experimental-features" error

If `nix develop` fails with an error about experimental features, enable flakes:

```bash
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### Shell doesn't have expected tools

Make sure you're using the default shell which includes all tools:

```bash
nix develop ./nix
```

Language-specific shells (e.g., `./nix#python`) only include that language's tools.

## Bazel

### Remote cache connection failures

If CI builds fail with remote cache errors, they fall back to local builds automatically. The remote cache runs on `bazel-remote-cache.seaweedfs.svc.cluster.local:8080`.

For local development, the disk cache at `~/.cache/bazel/disk_cache` is always used.

### Stale build artifacts

```bash
bazel clean --expunge
```

### Python dependency resolution failures

If pip resolution fails during `bazel build`, regenerate the lock file:

```bash
cd apps/<app>
uv pip compile requirements.in -o requirements_lock.txt
```

## Docker / Containers

### Cannot pull base images

Base images are proxied through Nexus. If the Nexus CA is not trusted, you may see TLS errors. The Nix shell sets up the CA bundle automatically.

### Image build fails on ARM

Ensure you're using the correct platform config:

```bash
bazel build --config=arm64 //apps/...
```

## Tests

### System tests fail to connect

Ensure infrastructure is running:

```bash
docker compose -f infra/sandbox/localhost/docker-compose.yaml up -d
```

Check service health:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8083/graphql   # GraphQL
```

### Pre-commit hooks fail

Run hooks manually to see detailed output:

```bash
pre-commit run --all-files --verbose
```

Common issues:

- **Ruff:** formatting or lint errors in Python code
- **mypy:** type errors (check `pyproject.toml` for configuration)
- **gofmt:** Go formatting (auto-fixed by the hook)
- **Buildifier:** Bazel file formatting (auto-fixed by the hook)
