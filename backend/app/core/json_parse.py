"""Tolerant JSON extraction from model output.

Models occasionally wrap JSON in markdown fences or surrounding prose, so we
isolate the outermost object before parsing and fall back to an empty dict.
"""

import json
import re


def parse_json_object(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
