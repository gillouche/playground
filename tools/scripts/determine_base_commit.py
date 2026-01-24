#!/usr/bin/env python3

import os
import ssl
import json
import urllib.request
import urllib.error
import subprocess
import concurrent.futures

NEXUS_URL = "https://nexus.gillouche.homelab"

def create_ssl_context(insecure=True):
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_git_tag_for_app(concept, app, ssl_context):
    """Fetch tags for an app and find the latest git-{sha}."""
    tags_url = f"{NEXUS_URL}/v2/docker-hosted/{concept}/{app}/tags/list"
    try:
        req = urllib.request.Request(tags_url)
        with urllib.request.urlopen(req, context=ssl_context, timeout=5) as response:
            data = json.loads(response.read().decode())
            tags = data.get("tags", [])
            
            # Filter for git tags and extract SHA
            git_shas = []
            for t in tags:
                if t.startswith("git-"):
                    sha = t[4:] # strip 'git-'
                    git_shas.append(sha)
            return git_shas
    except Exception:
        # App might not exist or error, return empty
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
    # 1. scan apps directory to find Apps to query (heuristic)
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    apps_root = os.path.join(workspace, "apps")
    
    apps_to_check = []
    
    if os.path.isdir(apps_root):
        for concept in os.listdir(apps_root):
            concept_path = os.path.join(apps_root, concept)
            if os.path.isdir(concept_path):
                for app in os.listdir(concept_path):
                    app_path = os.path.join(concept_path, app)
                    # Simple heuristic: must have a BUILD file (is a package)
                    if os.path.isdir(app_path) and \
                       (os.path.exists(os.path.join(app_path, "BUILD.bazel")) or \
                        os.path.exists(os.path.join(app_path, "BUILD"))):
                         apps_to_check.append((concept, app))

    if not apps_to_check:
        print("HEAD~1") # Fallback
        return

    ssl_ctx = create_ssl_context()
    found_shas = set()

    # 2. Query Nexus in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_git_tag_for_app, c, a, ssl_ctx): (c, a) for c, a in apps_to_check}
        for future in concurrent.futures.as_completed(futures):
            shas = future.result()
            found_shas.update(shas)
            
    if not found_shas:
        # No git tags found in registry, means first push ever?
        # Fallback to HEAD~1 is safer than failing, or initial commit?
        # HEAD~1 is 
        print("HEAD~1")
        return

    # 3. Resolve SHAs to find the most recent one reachable in history
    # We want the *newest* commit that is an ancestor of HEAD (or just exists)
    # Actually, we want the commit that is "closest" to HEAD?
    # No, we want the LATEST success.
    # If we have [C100, C99, C50] in registry.
    # Current HEAD is C101.
    # We want to diff C100..C101.
    # So we sort by timestamp and pick the latest one required.
    
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
    
    # Double check it is strictly older or equal to HEAD?
    # If current HEAD is C101. Registry has C100.
    # If registry has C102 (future?), we shouldn't use it as base.
    
    # Just print the SHA. existing git diff logic handles it.
    print(latest_sha)

if __name__ == "__main__":
    main()
