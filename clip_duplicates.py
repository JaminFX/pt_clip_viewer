"""Stable time-range deduplication without changing overlaps or group ownership."""
from bisect import bisect_right
import re

_LINE = re.compile(r"\s*([0-9]{2,}:[0-9]{2}:[0-9]{2}:[0-9]{2})\s*-\s*"
                   r"([0-9]{2,}:[0-9]{2}:[0-9]{2}:[0-9]{2})\s*")


def range_key(line):
    match = _LINE.fullmatch(line)
    if not match:
        return None
    start, end = (tuple(map(int, part.split(":"))) for part in match.groups())
    return (start, end) if start <= end else None


def unique_lines(lines):
    """Preserve first occurrence / order; normalize only the comparison key."""
    seen, result, duplicates = set(), [], 0
    for line in lines:
        key = range_key(line)
        key = ("range", key) if key is not None else ("text", line.strip())
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
            result.append(line)
    return result, duplicates


def new_lines(existing, incoming):
    """Skip identical or fully covered incoming ranges; keep partial overlaps.

    Build a coverage index once, including adjacent existing intervals. This
    recognizes an original clip inside an already merged line (and vice versa)
    without needing to guess a session frame rate or trim any new material.
    """
    ranges = sorted(key for line in existing if (key := range_key(line)) is not None)
    coverage = []
    for start, end in ranges:
        if coverage and start <= coverage[-1][1]:
            coverage[-1] = (coverage[-1][0], max(coverage[-1][1], end))
        else:
            coverage.append((start, end))
    starts = [start for start, _ in coverage]
    existing_text = {line.strip() for line in existing}
    candidates, duplicates = unique_lines(incoming)
    result = []
    for line in candidates:
        key = range_key(line)
        covered = line.strip() in existing_text
        if key is not None:
            start, end = key
            index = bisect_right(starts, start) - 1
            covered = covered or (index >= 0 and end <= coverage[index][1])
        if covered:
            duplicates += 1
        else:
            result.append(line)
    return result, duplicates
