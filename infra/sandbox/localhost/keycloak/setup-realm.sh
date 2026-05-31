#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REALM_JSON="$SCRIPT_DIR/api-lab-realm.json"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8180}"
ADMIN_USER="${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${KC_BOOTSTRAP_ADMIN_PASSWORD:-admin}"

echo "Waiting for Keycloak at $KEYCLOAK_URL..."
until curl -sf "$KEYCLOAK_URL/realms/master" > /dev/null 2>&1; do
    sleep 2
done
echo "Keycloak is ready."

ADMIN_TOKEN=$(curl -sf -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -d "grant_type=password&client_id=admin-cli&username=$ADMIN_USER&password=$ADMIN_PASS" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

AUTH_HEADER="Authorization: Bearer $ADMIN_TOKEN"

REALM_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH_HEADER" \
    "$KEYCLOAK_URL/admin/realms/api-lab")

if [ "$REALM_EXISTS" = "404" ]; then
    echo "Creating api-lab realm..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d @"$REALM_JSON" \
        "$KEYCLOAK_URL/admin/realms")
    if [ "$HTTP_CODE" = "201" ]; then
        echo "Realm created successfully."
    else
        echo "ERROR: Failed to create realm (HTTP $HTTP_CODE)"
        exit 1
    fi
else
    echo "Realm api-lab already exists, skipping creation."
fi

ADMIN_TOKEN=$(curl -sf -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -d "grant_type=password&client_id=admin-cli&username=$ADMIN_USER&password=$ADMIN_PASS" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH_HEADER="Authorization: Bearer $ADMIN_TOKEN"

SA_USER_ID=$(curl -sf -H "$AUTH_HEADER" \
    "$KEYCLOAK_URL/admin/realms/api-lab/users?username=service-account-api-lab-auth-service" | \
    python3 -c "import sys,json; users=json.load(sys.stdin); print(users[0]['id'] if users else '')")

if [ -n "$SA_USER_ID" ]; then
    RM_CLIENT_ID=$(curl -sf -H "$AUTH_HEADER" \
        "$KEYCLOAK_URL/admin/realms/api-lab/clients?clientId=realm-management" | \
        python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

    MANAGE_USERS=$(curl -sf -H "$AUTH_HEADER" \
        "$KEYCLOAK_URL/admin/realms/api-lab/clients/$RM_CLIENT_ID/roles/manage-users")

    MANAGE_REALM=$(curl -sf -H "$AUTH_HEADER" \
        "$KEYCLOAK_URL/admin/realms/api-lab/clients/$RM_CLIENT_ID/roles/manage-realm")

    curl -s -o /dev/null -w "" -X POST \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        "$KEYCLOAK_URL/admin/realms/api-lab/users/$SA_USER_ID/role-mappings/clients/$RM_CLIENT_ID" \
        -d "[$MANAGE_USERS, $MANAGE_REALM]" || true

    echo "Service account roles assigned."
else
    echo "WARNING: service-account-api-lab-auth-service user not found, skipping role assignment."
fi

echo "Keycloak api-lab realm setup complete."
