import sys
import json
import re
import subprocess

def query_targets(service_path):
    """Query bazel to find available targets for a service."""
    try:
        result = subprocess.run(
            ["bazel", "query", f"kind(sh_binary, //{service_path}/...)"],
            capture_output=True,
            text=True,
            timeout=30
        )
        targets = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return {
            "has_lint": any(t.endswith(":lint") for t in targets),
            "has_unit_test": any(t.endswith(":unit_test") for t in targets),
            "has_integration_test": any(t.endswith(":integration_test") for t in targets),
        }
    except Exception as e:
        print(f"Warning: Failed to query targets for {service_path}: {e}", file=sys.stderr)
        # Default to true so CI attempts to run them (will fail gracefully if missing)
        return {"has_lint": True, "has_unit_test": True, "has_integration_test": True}

def main():
    # Read targets from stdin
    targets = sys.stdin.read().split()

    services = {}

    # Regex to capture //apps/<concept>/<service>
    # Assumes structure: //apps/demo-app/greeting-service/...
    service_pattern = re.compile(r"//apps/([^/]+)/([^/:]+)")

    for target in targets:
        match = service_pattern.match(target)
        if match:
            concept = match.group(1)
            service_name = match.group(2)

            # Filter out 'deploy' folder if it appears as a service
            if service_name == "deploy":
                continue

            full_path = f"apps/{concept}/{service_name}"
            if full_path not in services:
                services[full_path] = {"name": service_name, "path": full_path}

    # Query available targets for each service
    for path, service in services.items():
        target_info = query_targets(path)
        service.update(target_info)

    # Sort for deterministic output
    sorted_services = sorted(services.values(), key=lambda x: x['name'])

    # Output compact JSON for GitHub Actions
    print(json.dumps(sorted_services))

if __name__ == "__main__":
    main()
