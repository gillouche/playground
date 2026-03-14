#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DONE = "DONE"
STUB = "STUB"
NA = "N/A"

COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_GRAY = "\033[90m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

STATUS_EMOJI = {DONE: "\u2705", STUB: "\U0001f7e1", NA: "\u2796"}


def find_repo_root():
    try:
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def parse_openapi(path):
    endpoints = []
    current_path = None
    current_method = None
    with Path(path).open() as f:
        for line in f:
            path_match = re.match(r"^  (/\S+):$", line)
            if path_match:
                current_path = path_match.group(1)
                current_method = None
                continue
            if current_path:
                method_match = re.match(r"^    (get|post|put|delete|patch):$", line)
                if method_match:
                    current_method = method_match.group(1).upper()
                    continue
            if current_path and current_method:
                op_match = re.match(r"^      operationId:\s+(\S+)", line)
                if op_match:
                    endpoints.append(
                        {
                            "method": current_method,
                            "path": current_path,
                            "operation_id": op_match.group(1),
                        }
                    )
                    current_method = None
                    continue
            if re.match(r"^\S", line) and not line.startswith("#"):
                current_path = None
                current_method = None
    return endpoints


def parse_proto(path):
    methods = []
    in_service = False
    with Path(path).open() as f:
        for line in f:
            if re.match(r"^service\s+\w+\s*\{", line):
                in_service = True
                continue
            if in_service:
                if line.strip() == "}":
                    break
                m = re.search(r"rpc\s+(\w+)\(", line)
                if m:
                    methods.append(m.group(1))
    return methods


def analyze_go_rest(main_go_path, endpoints):
    results = {}
    try:
        content = Path(main_go_path).read_text()
    except FileNotFoundError:
        return {e["operation_id"]: NA for e in endpoints}

    go_method_map = {
        "listBooks": "ListBooks",
        "createBook": "CreateBook",
        "getBook": "GetBook",
        "updateBook": "UpdateBook",
        "deleteBook": "DeleteBook",
        "getInventory": "GetInventory",
        "createReservations": "CreateReservations",
        "listReservations": "ListReservations",
        "getReservation": "GetReservation",
        "returnReservation": "ReturnReservation",
        "healthCheck": "HealthCheck",
        "readinessCheck": "ReadinessCheck",
        "serviceInfo": "ServiceInfo",
    }

    for ep in endpoints:
        op_id = ep["operation_id"]
        go_name = go_method_map.get(op_id, op_id)
        pattern = rf"func\s+\([^)]+\)\s+{go_name}\b[^{{]*\{{[^}}]*errNotImplemented"
        if re.search(pattern, content, re.DOTALL):
            results[op_id] = STUB
        elif re.search(rf"func\s+\([^)]+\)\s+{go_name}\b", content):
            results[op_id] = DONE
        else:
            results[op_id] = STUB
    return results


def analyze_go_grpc(main_go_path):
    try:
        content = Path(main_go_path).read_text()
    except FileNotFoundError:
        return None
    if re.search(r'^\s*"google\.golang\.org/grpc', content, re.MULTILINE):
        return True
    return None


def analyze_ts_rest(index_ts_path, endpoints):
    results = {}
    try:
        content = Path(index_ts_path).read_text()
    except FileNotFoundError:
        return {e["operation_id"]: NA for e in endpoints}

    ts_method_map = {
        "listBooks": "listBooks",
        "createBook": "createBook",
        "getBook": "getBook",
        "updateBook": "updateBook",
        "deleteBook": "deleteBook",
        "getInventory": "getInventory",
        "createReservations": "createReservations",
        "listReservations": "listReservations",
        "getReservation": "getReservation",
        "returnReservation": "returnReservation",
        "healthCheck": "healthCheck",
        "readinessCheck": "readinessCheck",
        "serviceInfo": "serviceInfo",
    }

    for ep in endpoints:
        op_id = ep["operation_id"]
        ts_name = ts_method_map.get(op_id, op_id)
        pattern = rf"async\s+{ts_name}\b[^{{]*\{{[^}}]*Not implemented"
        if re.search(pattern, content, re.DOTALL):
            results[op_id] = STUB
        elif re.search(rf"async\s+{ts_name}\b", content):
            results[op_id] = DONE
        else:
            results[op_id] = STUB
    return results


def analyze_ts_grpc(index_ts_path):
    try:
        content = Path(index_ts_path).read_text()
    except FileNotFoundError:
        return None
    if re.search(r"""(from\s+['"]@grpc/grpc-js|require\s*\(\s*['"]@grpc/grpc-js)""", content):
        return True
    return None


def format_status(status, use_color):
    if not use_color:
        return status
    colors = {DONE: COLOR_GREEN, STUB: COLOR_YELLOW, NA: COLOR_GRAY}
    return f"{colors.get(status, '')}{status}{COLOR_RESET}"


def render_table(title, rows, languages, use_color):
    name_col_width = max(len(r["name"]) for r in rows)
    name_col_width = max(name_col_width, len("Endpoint"))
    lang_col_width = 12

    header = f"  {'Endpoint':<{name_col_width}}"
    for lang in languages:
        header += f"  {lang:<{lang_col_width}}"

    if use_color:
        print(f"\n{COLOR_BOLD}{title}{COLOR_RESET}")
    else:
        print(f"\n{title}")
    print(header)

    for row in rows:
        line = f"  {row['name']:<{name_col_width}}"
        for lang in languages:
            status = row["status"].get(lang, NA)
            formatted = format_status(status, use_color)
            if use_color:
                line += f"  {formatted}{' ' * (lang_col_width - len(status))}"
            else:
                line += f"  {status:<{lang_col_width}}"
        print(line)


def compute_summary(rest_rows, grpc_rows, languages):
    summary = {}
    for lang in languages:
        rest_done = sum(1 for r in rest_rows if r["status"].get(lang) == DONE)
        grpc_done = sum(1 for r in grpc_rows if r["status"].get(lang) == DONE)
        rest_applicable = sum(1 for r in rest_rows if r["status"].get(lang) != NA)
        grpc_applicable = sum(1 for r in grpc_rows if r["status"].get(lang) != NA)
        total_done = rest_done + grpc_done
        total_applicable = rest_applicable + grpc_applicable
        pct = round(total_done / total_applicable * 100) if total_applicable else 0
        summary[lang] = {"done": total_done, "total": total_applicable, "percentage": pct}
    return summary


def render_markdown(rest_rows, grpc_rows, languages, summary):
    lines = []
    lines.append("## API Implementation Coverage\n")

    lines.append("### Summary\n")
    lines.append("| Language | Progress | Coverage |")
    lines.append("|----------|----------|----------|")
    for lang in languages:
        s = summary[lang]
        bar_filled = round(s["percentage"] / 5)
        bar = "\u2588" * bar_filled + "\u2591" * (20 - bar_filled)
        lines.append(
            f"| **{lang}** | `{bar}` | **{s['done']}/{s['total']}** ({s['percentage']}%) |"
        )

    lines.append("\n### REST Endpoints\n")
    lines.append("| Endpoint | " + " | ".join(languages) + " |")
    lines.append("|----------|" + "|".join(["----------|"] * len(languages)))
    for row in rest_rows:
        cells = []
        for lang in languages:
            status = row["status"].get(lang, NA)
            cells.append(f"{STATUS_EMOJI.get(status, '')} {status}")
        lines.append(f"| `{row['name']}` | " + " | ".join(cells) + " |")

    lines.append("\n### gRPC Methods\n")
    lines.append("| Method | " + " | ".join(languages) + " |")
    lines.append("|--------|" + "|".join(["----------|"] * len(languages)))
    for row in grpc_rows:
        cells = []
        for lang in languages:
            status = row["status"].get(lang, NA)
            cells.append(f"{STATUS_EMOJI.get(status, '')} {status}")
        lines.append(f"| `{row['name']}` | " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def build_coverage_data(repo_root):
    api_lab = Path(repo_root) / "apps" / "api-lab"
    openapi_path = api_lab / "openapi" / "openapi.yaml"
    proto_path = api_lab / "openapi" / "proto" / "library" / "v1" / "library.proto"
    go_main = api_lab / "go-api" / "main.go"
    ts_index = api_lab / "ts-api" / "src" / "index.ts"

    endpoints = parse_openapi(openapi_path)
    grpc_methods = parse_proto(proto_path)

    go_rest = analyze_go_rest(go_main, endpoints)
    go_has_grpc = analyze_go_grpc(go_main)
    ts_rest = analyze_ts_rest(ts_index, endpoints)
    ts_has_grpc = analyze_ts_grpc(ts_index)

    languages = ["Python", "Go", "TypeScript"]

    rest_rows = []
    for ep in endpoints:
        op_id = ep["operation_id"]
        display = f"{ep['method']} {ep['path']}"
        if len(display) > 35:
            display = display[:32] + "..."
        rest_rows.append(
            {
                "name": display,
                "operation_id": op_id,
                "status": {
                    "Python": DONE,
                    "Go": go_rest.get(op_id, STUB),
                    "TypeScript": ts_rest.get(op_id, STUB),
                },
            }
        )

    grpc_rows = []
    for method in grpc_methods:
        grpc_rows.append(
            {
                "name": method,
                "status": {
                    "Python": DONE,
                    "Go": STUB if go_has_grpc else NA,
                    "TypeScript": STUB if ts_has_grpc else NA,
                },
            }
        )

    summary = compute_summary(rest_rows, grpc_rows, languages)
    return endpoints, grpc_methods, rest_rows, grpc_rows, languages, summary


def main():
    parser = argparse.ArgumentParser(description="API Implementation Coverage Tracker")
    parser.add_argument("--repo-root", help="Repository root (auto-detected)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")
    parser.add_argument("--markdown", action="store_true", help="Markdown output")
    parser.add_argument(
        "--github-summary", action="store_true", help="Write markdown to $GITHUB_STEP_SUMMARY"
    )
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args = parser.parse_args()

    repo_root = args.repo_root or find_repo_root()
    if not repo_root:
        print("Could not determine repository root", file=sys.stderr)
        sys.exit(1)

    endpoints, grpc_methods, rest_rows, grpc_rows, languages, summary = build_coverage_data(
        repo_root
    )

    if args.json_output:
        report = {
            "rest": {
                "endpoints": [
                    {
                        "method": ep["method"],
                        "path": ep["path"],
                        "operation_id": ep["operation_id"],
                        "status": rest_rows[i]["status"],
                    }
                    for i, ep in enumerate(endpoints)
                ]
            },
            "grpc": {
                "methods": [
                    {"method": m, "status": grpc_rows[i]["status"]}
                    for i, m in enumerate(grpc_methods)
                ]
            },
            "summary": summary,
        }
        print(json.dumps(report, indent=2))
        return

    md = render_markdown(rest_rows, grpc_rows, languages, summary)

    if args.markdown:
        print(md)
        return

    if args.github_summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a") as f:
                f.write(md)
            print("Coverage report written to GitHub Step Summary")
        else:
            print("$GITHUB_STEP_SUMMARY not set, printing to stdout")
            print(md)
        return

    use_color = not args.no_color and sys.stdout.isatty()

    if use_color:
        print(f"\n{COLOR_BOLD}=== API Implementation Coverage ==={COLOR_RESET}")
    else:
        print("\n=== API Implementation Coverage ===")

    render_table("REST Endpoints (from openapi.yaml):", rest_rows, languages, use_color)
    render_table("gRPC Methods (from library.proto):", grpc_rows, languages, use_color)

    print("\nSummary:")
    for lang in languages:
        s = summary[lang]
        status_str = f"{s['done']}/{s['total']} ({s['percentage']:3d}%)"
        print(f"  {lang + ':':<14} {status_str}")

    print()


if __name__ == "__main__":
    main()
