import os
import shutil
import sys
import tarfile
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: package_app.py <output_tar> <src_file1> [src_file2 ...]")
        sys.exit(1)

    output_tar = sys.argv[1]
    srcs = sys.argv[2:]

    stage_dir = Path("app_stage")
    app_root = stage_dir / "app"

    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    app_root.mkdir(parents=True)

    print(f"Packaging {len(srcs)} files into {output_tar}...")

    for src in srcs:
        if "src/" in src:
            idx = src.rfind("src/")
            if idx != -1:
                rel_path = src[idx:]
                dest_path = app_root / rel_path

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest_path)
                print(f"Copied {src} -> {rel_path}")
            else:
                print(f"Skipping {src}: 'src/' not found")
        else:
            print(f"Skipping {src}: 'src/' not found")

    with tarfile.open(output_tar, "w") as tar:
        for root, _dirs, files in os.walk(stage_dir):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(stage_dir)
                tar_info = tar.gettarinfo(str(full_path), arcname=str(rel_path))
                tar_info.uid = 0
                tar_info.gid = 0
                tar_info.uname = "root"
                tar_info.gname = "root"
                tar_info.mtime = 0

                with full_path.open("rb") as f:
                    tar.addfile(tar_info, f)

    print(f"Successfully created {output_tar}")


if __name__ == "__main__":
    main()
