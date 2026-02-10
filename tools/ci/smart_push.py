#!/usr/bin/env python3
"""
Smart push script that only pushes OCI images if their digest differs from the registry.

This avoids pushing unchanged images, saving bandwidth and registry storage.
Uses crane for registry digest queries.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )


def get_local_image_digest(image_target: str) -> str | None:
    """Get the digest of a locally built OCI image using bazel."""
    # Build the image for ARM64 target platform
    # Note: We use --config=arm64 for building the image content,
    # but tools that run on the host still use host binaries
    result = run_command(["bazel", "build", "--config=ci", "--config=arm64", image_target])
    if result.returncode != 0:
        print(f"Failed to build {image_target}", file=sys.stderr)
        return None

    # Get the image digest from bazel-bin
    # The oci_image rule creates a directory with an index.json
    # Parse the target to find the output path
    target_parts = image_target.split(":")
    package = target_parts[0].lstrip("/")
    name = target_parts[1] if len(target_parts) > 1 else target_parts[0].split("/")[-1]

    # Find the image directory in bazel-bin
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY", os.getcwd())
    image_dir = Path(workspace_dir) / "bazel-bin" / package / name

    index_path = image_dir / "index.json"
    if not index_path.exists():
        print(f"Image index not found at {index_path}", file=sys.stderr)
        return None

    with open(index_path) as f:
        index = json.load(f)

    # Get the digest from the manifest
    if "manifests" in index and len(index["manifests"]) > 0:
        return index["manifests"][0].get("digest")

    return None


def get_remote_image_digest(repository: str, tag: str = "latest") -> str | None:
    """Get the digest of a remote image using crane."""
    result = run_command(["crane", "digest", f"{repository}:{tag}"])
    if result.returncode != 0:
        # Image might not exist yet
        return None
    return result.stdout.strip()


def get_push_targets() -> list[dict]:
    """Query all oci_push targets in the apps directory."""
    result = run_command(["bazel", "query", "kind(oci_push, //apps/...)"])
    if result.returncode != 0:
        print("Failed to query oci_push targets", file=sys.stderr)
        return []

    targets = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        # Get the image target (replace _push with _image)
        image_target = line.replace("_push", "_image")

        # Query the repository attribute
        repo_result = run_command([
            "bazel", "query",
            f"labels(repository, {line})",
            "--output=build"
        ])

        # Parse repository from build output (simplified - actual parsing would be more complex)
        # For now, we'll infer from the package path
        parts = line.split("/")
        # //apps/demo-app/greeting-service:greeting-service_push
        if len(parts) >= 4:
            app = parts[2]  # demo-app
            service = parts[3].split(":")[0]  # greeting-service
            repository = f"nexus.gillouche.homelab/docker-hosted/{app}/{service}"
        else:
            continue

        targets.append({
            "push_target": line,
            "image_target": image_target,
            "repository": repository,
        })

    return targets


def push_image(push_target: str, tags: list[str]) -> bool:
    """Push an image with the given tags."""
    tag_args = []
    for tag in tags:
        tag_args.extend(["--tag", tag])

    # Don't use --config=arm64 for the push - the push script runs on the host
    # and needs host-compatible tools (jq, etc.).
    cmd = ["bazel", "run", "--config=ci", push_target, "--"] + tag_args
    result = run_command(cmd, capture=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Smart push - only push changed images")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually push")
    parser.add_argument("--tag", action="append", default=[], help="Tags to apply (can be repeated)")
    parser.add_argument("--force", action="store_true", help="Push even if unchanged")
    args = parser.parse_args()

    if not args.tag:
        args.tag = ["latest"]

    # Get git SHA for tagging
    git_result = run_command(["git", "rev-parse", "--short", "HEAD"])
    if git_result.returncode == 0:
        sha_tag = git_result.stdout.strip()
        if sha_tag not in args.tag:
            args.tag.append(sha_tag)

    print(f"Tags to apply: {args.tag}")

    targets = get_push_targets()
    if not targets:
        print("No oci_push targets found")
        return 0

    pushed = 0
    skipped = 0
    failed = 0

    for target in targets:
        print(f"\nProcessing {target['push_target']}...")

        if not args.force:
            # Get local digest
            local_digest = get_local_image_digest(target["image_target"])
            if not local_digest:
                print(f"  Could not get local digest, will push anyway")
            else:
                print(f"  Local digest: {local_digest}")

                # Get remote digest
                remote_digest = get_remote_image_digest(target["repository"])
                if remote_digest:
                    print(f"  Remote digest: {remote_digest}")

                    if local_digest == remote_digest:
                        print(f"  SKIPPED: Image unchanged")
                        skipped += 1
                        continue
                else:
                    print(f"  Remote image not found, will push")

        if args.dry_run:
            print(f"  DRY-RUN: Would push with tags {args.tag}")
            pushed += 1
        else:
            print(f"  Pushing with tags {args.tag}...")
            if push_image(target["push_target"], args.tag):
                print(f"  PUSHED successfully")
                pushed += 1
            else:
                print(f"  FAILED to push")
                failed += 1

    print(f"\n{'='*50}")
    print(f"Summary: {pushed} pushed, {skipped} skipped, {failed} failed")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
