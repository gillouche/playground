# Scaling api-lab

api-lab Python services are scaled automatically by KEDA based on HTTP request
rate (see `apps/api-lab/<service>/deploy/templates/scaledobject.ytt.yaml`).
Manual overrides are sometimes necessary during incidents.

## Inspect current scale

```bash
kubectl -n playground-apps-dev-api-lab get rollouts
kubectl -n playground-apps-dev-api-lab get scaledobjects
kubectl -n playground-apps-dev-api-lab get hpa
```

## Bump min/max replicas (dev only)

Edit the relevant `scaledobject.ytt.yaml`, regenerate, commit:

```bash
$EDITOR apps/api-lab/python-api/deploy/templates/scaledobject.ytt.yaml
./tools/deploy/ytt_gen.sh --env dev api-lab python-api
git diff apps/api-lab/deploy/dev/python-api-scaledobject.yaml
```

ArgoCD will pick up the change after the PR is merged. To accelerate while the
PR is pending, you can suspend the KEDA-managed HPA temporarily and set
replicas manually:

```bash
kubectl -n playground-apps-dev-api-lab annotate scaledobject python-api \
  autoscaling.keda.sh/paused-replicas="3"
```

Remove the annotation to resume normal scaling.

## Quick replica change for a single rollout

```bash
kubectl argo rollouts -n playground-apps-dev-api-lab set replicas python-api 3
```

This is reverted by ArgoCD on the next reconcile unless KEDA scaling is paused.

## When to scale

- `api_lab_rate_limit_rejections_total` climbing: serve more capacity for the
  hot tier, or tune `RATE_LIMIT_*` env vars.
- DB CPU saturated: scaling pods won't help — investigate query performance
  via `api_lab_db_query_duration_seconds`.
- Cache hit rate low: scale Redis or warm caches before scaling app.

See the `api-lab` Grafana dashboard for the current state.
