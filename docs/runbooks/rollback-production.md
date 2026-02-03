# Rollback Production

## Emergency Undo
If Prod is broken, revert to the previous known-good version.

```bash
bazel run //tools:rollback -- --app demo-app --target prod --commit
```

## What it does
1.  Looks at git history for `apps/demo-app/deploy/prod/kustomization.yaml`.
2.  Finds the previously deployed version tag (e.g., went from v1.0.0 -> v1.0.1, it finds v1.0.0).
3.  Verifies `releases/versions/demo-app/v1.0.0.yaml` exists.
4.  Re-applies v1.0.0 to Prod.
5.  Commits the revert.

## Manual Option
You can also just promote an old version specifically:
```bash
bazel run //tools:promote -- --app demo-app --version v1.0.0 --target prod
```
