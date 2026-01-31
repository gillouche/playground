import os
import sys
import shutil
import tarfile

def main():
    if len(sys.argv) < 3:
        print("Usage: package_app.py <output_tar> <src_file1> [src_file2 ...]")
        sys.exit(1)

    output_tar = sys.argv[1]
    srcs = sys.argv[2:]
    
    # Staging directory
    stage_dir = "app_stage"
    app_root = os.path.join(stage_dir, "app")
    
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir)
    os.makedirs(app_root)

    print(f"Packaging {len(srcs)} files into {output_tar}...")

    for src in srcs:
        # We want to preserve structure starting from 'src/'
        # e.g. apps/demo-app/infra-check-service/src/main.py -> /app/src/main.py
        
        if "src/" in src:
            idx = src.rfind("src/")
            if idx != -1:
                rel_path = src[idx:] # e.g. src/main.py
                dest_path = os.path.join(app_root, rel_path)
                
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src, dest_path)
                print(f"Copied {src} -> {rel_path}")
            else:
                print(f"Skipping {src}: 'src/' not found")
        else:
             print(f"Skipping {src}: 'src/' not found")
    
    with tarfile.open(output_tar, "w") as tar:
        # We scan app_stage directory
        for root, dirs, files in os.walk(stage_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, stage_dir)
                # Set deterministic info
                tar_info = tar.gettarinfo(full_path, arcname=rel_path)
                tar_info.uid = 0
                tar_info.gid = 0
                tar_info.uname = "root"
                tar_info.gname = "root"
                tar_info.mtime = 0 # Deterministic timestamp
                
                with open(full_path, "rb") as f:
                    tar.addfile(tar_info, f)
                    
    print(f"Successfully created {output_tar}")

if __name__ == "__main__":
    main()
