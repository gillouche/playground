# Debugging api-lab auth (Keycloak / JWT)

When users get `401 Invalid token: <reason>` or python-auth-api returns 5xx,
walk through the steps below in order.

## 1. Are the services ready?

```bash
kubectl -n playground-apps-dev-api-lab get pods
kubectl -n playground-apps-dev-api-lab exec deploy/python-rest-api -- \
  curl -s localhost:8080/ready
kubectl -n playground-apps-dev-api-lab exec deploy/python-auth-api -- \
  curl -s localhost:8084/ready
```

A non-ready response lists the missing dependency (jwt_validator, postgres,
redis, keycloak). Fix that first.

## 2. Is Keycloak reachable from the namespace?

```bash
kubectl -n playground-apps-dev-api-lab run -it --rm jwt-debug \
  --image=curlimages/curl --restart=Never -- \
  curl -fsSL http://keycloak.playground-infra-dev.svc.cluster.local:8080/realms/api-lab/.well-known/openid-configuration
```

If this fails, the egress NetworkPolicy is the usual suspect — confirm port
8080 is allowed in `python-auth-api-egress-networkpolicy.yaml`.

## 3. Is the JWT signed by the realm we expect?

Decode the offending token (do **not** paste real prod tokens):

```bash
echo "<jwt>" | cut -d. -f2 | base64 -d | jq
```

Check:

- `iss` matches `http://keycloak.playground-infra-dev.svc.cluster.local:8080/realms/api-lab`
- `aud` includes the service's `client_id` (e.g. `api-lab`)
- `exp` is in the future

If `iss`/`aud` mismatch, the Keycloak realm config is drifting — see
`infra/sandbox/localhost/keycloak/setup-realm.sh` for the canonical state.

## 4. Are the JWKs fresh?

The validator caches the JWKs set for 300s (`JWTValidator.__init__`). If the
realm rotates signing keys mid-session, expect a one-time spike of
`invalid_signature` errors. Restart the rollout to force a fresh fetch:

```bash
kubectl argo rollouts -n playground-apps-dev-api-lab restart python-rest-api
kubectl argo rollouts -n playground-apps-dev-api-lab restart python-auth-api
kubectl argo rollouts -n playground-apps-dev-api-lab restart python-grpc-api
```

## 5. Inspect the security event log

```bash
kubectl -n playground-apps-dev-api-lab logs deploy/python-auth-api | \
  jq 'select(.event=="login_failure" or .event=="auth_failure")'
```

`reason` values: `expired`, `invalid_signature`, `invalid_issuer`,
`invalid_audience`, `malformed`, `missing_sub`, `validation_failed:*`.

## 6. Common root causes

| Symptom                        | Likely cause                                                |
|--------------------------------|-------------------------------------------------------------|
| All tokens fail `invalid_audience` | Client id changed but `KEYCLOAK_CLIENT_ID` env not updated |
| All tokens fail `invalid_issuer`   | Keycloak service URL mismatch (env vs configmap)         |
| Sporadic `expired` after login     | Clock skew between Keycloak and app nodes                |
| `Service not initialized` (503)    | python-auth-api pod restarted but readiness lagging      |
