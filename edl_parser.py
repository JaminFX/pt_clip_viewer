"""Bounded local file reading and linear scanning of Pro Tools text exports."""
import os
import re
import stat

MAX_EDL_BYTES = 20 * 1024 * 1024
_HEADER = re.compile(r"(?:TRACK NAME:|轨道名[：:])[ \t]*(.+)")
_TC = r"[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2}"
_TIMES = re.compile(f"({_TC})[ \\t]+({_TC})[ \\t]+({_TC})")


def read_export(filepath):
    # Validate the opened descriptor, not a separate path stat. Nonblocking open
    # also prevents a named pipe from blocking before the regular-file check.
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(filepath, flags)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("请选择普通文本文件")
        content = stream.read(MAX_EDL_BYTES + 1)
    if len(content) > MAX_EDL_BYTES:
        raise ValueError("文件超过 20 MB，已拒绝读取")
    for encoding in ("utf-8-sig", "utf-16", "gbk", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeError:
            continue
    return ""


def parse_edl(filepath):
    text = read_export(filepath)
    tracks = []
    current = None
    seen = set()
    for line in text.splitlines():
        header = _HEADER.match(line)
        if header:
            if current and current["clips"]:
                tracks.append(current)
            current = {"track_name": header.group(1).strip(), "clips": []}
            seen = set()
            continue
        if current is None or not line.startswith("1"):
            continue
        fields = line.split(None, 2)
        if len(fields) != 3 or fields[0] != "1" or not fields[1].isascii() or not fields[1].isdigit():
            continue
        event, remainder = fields[1:]
        if event in seen:
            continue
        # Find fixed-width time fields first. Never combine a lazy arbitrary
        # clip-name match with an ambiguous variable-length whitespace match.
        for times in _TIMES.finditer(remainder):
            position = times.start()
            if not position or remainder[position-1] not in " \t":
                continue
            if remainder[position-1] != "\t" and (position < 2 or remainder[position-2] not in " \t"):
                continue
            prefix = remainder[:position]
            name = prefix.rstrip(" \t")
            separation = prefix[len(name):]
            if not name or (len(separation) < 2 and "\t" not in separation):
                continue
            current["clips"].append({"event": event, "name": name,
                                     "start": times[1], "end": times[2], "duration": times[3]})
            seen.add(event)
            break
    if current and current["clips"]:
        tracks.append(current)
    return tracks
