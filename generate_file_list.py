import argparse
import glob
import os
import random
import sys

def get_file_list(path, glob_pattern, sort_method, sort_ascending, seed, allowed_extensions):
    if allowed_extensions is None or allowed_extensions.strip() == "":
        allowed = []
    else:
        allowed = [ext.strip().lower() for ext in allowed_extensions.split(',') if ext.strip()]
    pattern = os.path.join(path.rstrip("/\\"), glob_pattern)
    files = glob.glob(pattern, recursive=True)
    if len(allowed) > 0:
        filtered = [f for f in files if any(f.lower().endswith(ext) for ext in allowed)]
    else:
        filtered = files

    # Sorting logic
    if sort_method == "date":
        filtered.sort(key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 0, reverse=not sort_ascending)
    elif sort_method == "filename":
        filtered.sort(key=lambda f: os.path.basename(f).lower(), reverse=not sort_ascending)
    elif sort_method == "parent folder":
        filtered.sort(key=lambda f: os.path.dirname(f).lower(), reverse=not sort_ascending)
    elif sort_method == "full path":
        filtered.sort(key=lambda f: os.path.abspath(f).lower(), reverse=not sort_ascending)
    elif sort_method == "random":
        random.seed(seed)
        random.shuffle(filtered)
    # "default" does not sort
    return filtered

def main():
    parser = argparse.ArgumentParser(description="Generate a text file with a list of files matching criteria.")
    parser.add_argument("--path", type=str, default="./", help="Base path to search (default: ./)")
    parser.add_argument("--glob_pattern", type=str, default="**/*", help="Glob pattern (default: **/*)")
    parser.add_argument("--sort", type=str, choices=["default", "date", "filename", "parent folder", "full path", "random"], default="default", help="Sort method (default: default)")
    parser.add_argument("--ascending", type=lambda x: (str(x).lower() in ['true', '1', 'yes']), default=True, help="Sort ascending (default: True)")
    parser.add_argument("--allowed_extensions", type=str, default=".jpeg,.jpg,.png,.tiff,.gif,.bmp,.webp", help="Comma-separated allowed extensions (default: .jpeg,.jpg,.png,.tiff,.gif,.bmp,.webp)")
    parser.add_argument("--seed", type=int, default=0, help="Seed for random sort (default: 0)")
    parser.add_argument("--new_files_only", type=lambda x: (str(x).lower() in ['true', '1', 'yes']), default=False, help="Only include new files (default: False)")
    parser.add_argument("--dest_path", type=str, default="./", help="Destination path for new files (default: ./)")
    parser.add_argument("--output", type=str, default="file_list.txt", help="Output .txt file (default: file_list.txt)")
    parser.add_argument("--filter", type=str, default="", help="list of strings, separated by commas, which must appear in returned files. If empty, all files are returned (default: '')")

    args = parser.parse_args()



    file_list = get_file_list(
        args.path,
        args.glob_pattern,
        args.sort,
        args.ascending,
        args.seed,
        args.allowed_extensions
    )

    # If new_files_only is set, filter out files that have corresponding files in dest_path
    if args.new_files_only:
        filtered_list = []
        for file in file_list:
            rel_path = os.path.relpath(file, args.path)
            dest_dir = os.path.join(args.dest_path, os.path.dirname(rel_path))
            base = os.path.splitext(os.path.basename(file))[0]
            ext = os.path.splitext(file)[1]
            # Match files like base-*.ext
            pattern = os.path.join(dest_dir, f"{base}-*")
            matches = glob.glob(pattern)
            if not matches:
                filtered_list.append(file)
        file_list = filtered_list

    # Apply filter argument if provided
    if args.filter.strip():
        filter_strings = [s.strip().lower() for s in args.filter.split(',') if s.strip()]
        if filter_strings:
            file_list = [f for f in file_list if any(s in f.lower() for s in filter_strings)]

    with open(args.output, "w", encoding="utf-8") as f:
        for file in file_list:
            f.write(file + "\n")

    print(f"File list written to {args.output} ({len(file_list)} files)")

if __name__ == "__main__":
    main()