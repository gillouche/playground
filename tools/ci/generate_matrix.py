import sys
import json
import re

def main():
    # Read targets from stdin
    targets = sys.stdin.read().split()

    services = set()

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
            services.add(json.dumps({"name": service_name, "path": full_path}))

    # Sort for deterministic output
    sorted_services = sorted([json.loads(s) for s in services], key=lambda x: x['name'])

    # Output compact JSON for GitHub Actions
    print(json.dumps(sorted_services))

if __name__ == "__main__":
    main()
