#!/usr/bin/env python3

import os
import ssl
import json
import urllib.request
import urllib.error
import subprocess
import concurrent.futures
import re

NEXUS_URL = "https://nexus.gillouche.homelab"

def create_ssl_context(insecure=True):
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_git_tag_for_component(app, component, ssl_context):
    """Fetch tags for a component and find valid git short SHAs."""
    # Nexus path: docker-hosted/{app}/{component}
    tags_url = f"{NEXUS_URL}/v2/docker-hosted/{app}/{component}/tags/list"
    try:
        req = urllib.request.Request(tags_url)
        with urllib.request.urlopen(req, context=ssl_context, timeout=5) as response:
            data = json.loads(response.read().decode())
            tags = data.get("tags", [])
            
            # Filter for short SHAs (7 chars hex), ignore 'latest', 'v*', etc.
            git_shas = []
            sha_pattern = re.compile(r"^[0-9a-f]{7,40}$") 
            
            for t in tags:
                # smart_push pushes 'latest' and short SHA (usually 7 chars)
                if sha_pattern.match(t):
                    git_shas.append(t)
            return git_shas
    except Exception:
        # Component might not exist or error, return empty
        return []

def get_commit_timestamp(sha):
    """Get commit timestamp for sorting."""
    try:
        # Check if object exists in local git
        subprocess.check_call(["git", "cat-file", "-e", sha], stderr=subprocess.DEVNULL)
        ts = subprocess.check_output(["git", "show", "-s", "--format=%ct", sha]).strip()
        return int(ts)
    except:
        return 0

def main():
    # 1. scan apps directory to find components to query
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    apps_root = os.path.join(workspace, "apps")
    
    components_to_check = []
    
    if os.path.isdir(apps_root):
        for app in os.listdir(apps_root):
            app_path = os.path.join(apps_root, app)
            if os.path.isdir(app_path):
                for component in os.listdir(app_path):
                    comp_path = os.path.join(app_path, component)
                    # Exclude 'deploy' folder (contains kustomization for app)
                    if component == "deploy":
                        continue
                        
                    # Simple heuristic: must have a BUILD file (is a package)
                    if os.path.isdir(comp_path) and \
                       (os.path.exists(os.path.join(comp_path, "BUILD.bazel")) or \
                        os.path.exists(os.path.join(comp_path, "BUILD"))):
                         components_to_check.append((app, component))

    if not components_to_check:
        print("HEAD~1") # Fallback
        return

    ssl_ctx = create_ssl_context()
    found_shas = set()

    # 2. Query Nexus in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_git_tag_for_component, a, c, ssl_ctx): (a, c) for a, c in components_to_check}
        for future in concurrent.futures.as_completed(futures):
            shas = future.result()
            found_shas.update(shas)
            
    if not found_shas:
        # No git tags found in registry
        print("HEAD~1")
        return

    # 3. Resolve SHAs to find the most recent one reachable in history
    sorted_commits = []
    for sha in found_shas:
        ts = get_commit_timestamp(sha)
        if ts > 0:
            sorted_commits.append((ts, sha))
            
    if not sorted_commits:
        print("HEAD~1")
        return
        
    # Sort descending by timestamp
    sorted_commits.sort(key=lambda x: x[0], reverse=True)
    
    # Return the SHA of the most recent commit
    latest_sha = sorted_commits[0][1]
    
    print(latest_sha)

if __name__ == "__main__":
    main()
