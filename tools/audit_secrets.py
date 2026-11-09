"""Scan project files, Git history and bundled project modules without printing secrets."""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

RULES = {
    "github-token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})",
    "openai-key": rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}",
    "aws-access-key": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "slack-webhook": rb"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}",
    "credential-uri": rb"(?:postgresql|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s/@]+@[^\s]+",
    "literal-password": rb"(?i)(?:password|api_key|access_token|client_secret)\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{16,}['\"]",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--pyinstaller", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    findings, counts = [], {"files": 0, "history_blobs": 0, "archive_members": 0, "bundled_modules": 0}

    def scan(label, data):
        for kind, expression in RULES.items():
            for match in re.finditer(expression, data):
                findings.append({"location": label, "rule": kind,
                                 "line": data[:match.start()].count(b"\n")+1,
                                 "fingerprint": hashlib.sha256(match[0]).hexdigest()[:12],
                                 "value": "<redacted>"})

    for file in root.rglob("*"):
        rel = file.relative_to(root)
        if any(part in (".git", "build", "__pycache__", ".venv-build", ".venv-macos") for part in rel.parts):
            continue
        if file.is_symlink() or not file.is_file():
            continue
        if file.stat().st_size > 128*1024*1024:
            continue
        scan(rel.as_posix(), file.read_bytes())
        counts["files"] += 1
        if file.suffix == ".zip":
            with zipfile.ZipFile(file) as archive:
                for entry in archive.infolist():
                    if entry.file_size <= 4*1024*1024 and Path(entry.filename).suffix in (".py", ".txt", ".json", ".md", ".ini", ".env"):
                        scan(rel.as_posix()+"!"+entry.filename, archive.read(entry))
                        counts["archive_members"] += 1
    helper = root / "build" / "github_ops.py"
    if helper.is_file():
        scan("local-only github_ops.py", helper.read_bytes())
    if args.repo:
        objects = subprocess.check_output(["git", "-C", str(args.repo), "rev-list", "--objects", "--all"], text=True, encoding="utf-8", errors="replace")
        for item in objects.splitlines():
            fields = item.split(" ", 1)
            if len(fields) != 2:
                continue
            oid, path = fields
            kind = subprocess.check_output(["git", "-C", str(args.repo), "cat-file", "-t", oid], text=True, encoding="utf-8", errors="replace").strip()
            if kind == "blob":
                data = subprocess.check_output(["git", "-C", str(args.repo), "cat-file", "blob", oid])
                scan("git:"+oid[:12]+":"+path, data)
                counts["history_blobs"] += 1
    if args.pyinstaller:
        from PyInstaller.archive.readers import CArchiveReader
        reader = CArchiveReader(str(args.pyinstaller))
        names = ("pt_clip_viewer", "edl_parser", "ui_widgets", "aa_graphics", "pt_platform", "ui_validation")
        for name in names:
            if name in reader.toc:
                scan("bundled:"+name, reader.extract(name))
                counts["bundled_modules"] += 1
        for archive_name in reader.toc:
            if archive_name.endswith(".pyz"):
                embedded = reader.open_embedded_archive(archive_name)
                for name in names:
                    if name in embedded.toc:
                        scan("bundled:"+name, embedded.extract(name, raw=True))
                        counts["bundled_modules"] += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"counts": counts, "findings": findings,
                                      "limitations": "Pattern-based scan; native binary decompilation and unknown/custom secret formats are not covered."},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": counts, "findings": len(findings)}))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
