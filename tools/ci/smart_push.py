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
        check=False,
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
    workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY", str(Path.cwd()))
    image_dir = Path(workspace_dir) / "bazel-bin" / package / name

    index_path = image_dir / "index.json"
    if not index_path.exists():
        print(f"Image index not found at {index_path}", file=sys.stderr)
        return None

    with index_path.open() as f:
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
        run_command(["bazel", "query", f"labels(repository, {line})", "--output=build"])

        parts = line.split("/")
        # //apps/demo-app/greeting-service:greeting-service_push
        if len(parts) >= 4:
            app = parts[2]  # demo-app
            service = parts[3].split(":")[0]  # greeting-service
            repository = f"nexus.gillouche.homelab/docker-hosted/{app}/{service}"
        else:
            continue

        targets.append(
            {
                "push_target": line,
                "image_target": image_target,
                "repository": repository,
            }
        )

    return targets


def push_image(push_target: str, tags: list[str]) -> bool:
    """Push an image with the given tags."""
    tag_args = []
    for tag in tags:
        tag_args.extend(["--tag", tag])

    # Don't use --config=arm64 for the push - the push script runs on the host
    # and needs host-compatible tools (jq, etc.).
    cmd = ["bazel", "run", "--config=ci", push_target, "--", *tag_args]
    result = run_command(cmd, capture=False)
    return result.returncode == 0


def resolve_tags(tags: list[str]) -> list[str]:
    """Resolve the final list of tags, adding git SHA if available."""
    if not tags:
        tags = ["latest"]

    git_result = run_command(["git", "rev-parse", "--short", "HEAD"])
    if git_result.returncode == 0:
        sha_tag = git_result.stdout.strip()
        if sha_tag not in tags:
            tags.append(sha_tag)

    return tags


def should_skip_target(target: dict) -> bool:
    """Return True if the target image is unchanged and should be skipped."""
    local_digest = get_local_image_digest(target["image_target"])
    if not local_digest:
        print("  Could not get local digest, will push anyway")
        return False

    print(f"  Local digest: {local_digest}")
    remote_digest = get_remote_image_digest(target["repository"])
    if not remote_digest:
        print("  Remote image not found, will push")
        return False

    print(f"  Remote digest: {remote_digest}")
    if local_digest == remote_digest:
        print("  SKIPPED: Image unchanged")
        return True

    return False


def execute_push(push_target: str, tags: list[str], dry_run: bool) -> str:
    """Push or simulate pushing an image. Returns 'pushed' or 'failed'."""
    if dry_run:
        print(f"  DRY-RUN: Would push with tags {tags}")
        return "pushed"

    print(f"  Pushing with tags {tags}...")
    if push_image(push_target, tags):
        print("  PUSHED successfully")
        return "pushed"

    print("  FAILED to push")
    return "failed"


def main():
    parser = argparse.ArgumentParser(description="Smart push - only push changed images")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually push")
    parser.add_argument(
        "--tag", action="append", default=[], help="Tags to apply (can be repeated)"
    )
    parser.add_argument("--force", action="store_true", help="Push even if unchanged")
    args = parser.parse_args()

    args.tag = resolve_tags(args.tag)
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

        if not args.force and should_skip_target(target):
            skipped += 1
            continue

        result = execute_push(target["push_target"], args.tag, args.dry_run)
        if result == "pushed":
            pushed += 1
        else:
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Summary: {pushed} pushed, {skipped} skipped, {failed} failed")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
