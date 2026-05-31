# api-lab deploy

This project only generates manifests for the `dev` environment. `test` and
`prod` manifests are produced later by `bazel run //tools/release:promote`
once a `dev` build is validated; do not hand-write them here.

## Layout

- `base/` — shared resources (PDB, default ingress NetworkPolicy)
- `rollouts-base/` — Argo Rollouts analysis templates
- `dev/` — generated per-env manifests (do not hand-edit; see `tools/deploy/ytt_gen.sh`)
- `sandbox/` — local minikube manifests for `docker-compose`-style development

## Generating manifests

Manifests are rendered from `apps/api-lab/<component>/deploy/templates/` by
`tools/deploy/ytt_gen.sh`. Regenerate after any template change:

```bash
./tools/deploy/ytt_gen.sh --env dev api-lab
```

CI fails if the committed manifests differ from a fresh render.

## External secrets

This repository does **not** create SealedSecrets at apply time. All three
api-lab Python rollouts (`python-api`, `python-grpc-api`, `python-auth-api`)
read every credential they need from a single Secret:

- **`api-lab-credentials`** in namespace `playground-apps-<env>-api-lab`
- Keys:
  - `POSTGRES_PASSWORD`
  - `REDIS_PASSWORD`
  - `KEYCLOAK_CLIENT_SECRET`
  - `KEYCLOAK_AUTH_SERVICE_CLIENT_SECRET`

The non-secret connection details (`POSTGRES_HOST`, `POSTGRES_PORT`,
`POSTGRES_USER`, `POSTGRES_DB`, `REDIS_HOST`, `REDIS_PORT`, `KEYCLOAK_*` URLs
and client IDs) live in each service's ConfigMap.

### Source of truth

Plaintext templates for the Secret live in `secrets/<env>/api-lab-credentials.yaml`.
The gitops pipeline seals them with `kubeseal` and applies the resulting
SealedSecrets to the cluster.

The Keycloak client secret values (`KEYCLOAK_CLIENT_SECRET` and
`KEYCLOAK_AUTH_SERVICE_CLIENT_SECRET`) must match the `api-lab` and
`api-lab-auth-service` client secrets configured in the corresponding
Keycloak realm.

## Scope

This branch is the Python setup only. `go-api` and `ts-api` are intentionally
out of scope and not deployed.
