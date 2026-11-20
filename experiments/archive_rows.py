"""Read structured experiment columns across the team-ID change, preserving recorded speech."""

import csv
import json

from footsteps.record import legacy_roles


def current_id(value):
    for old, current in legacy_roles().items():
        value = value.replace("-" + old, "-" + current)
    return value


def current_row(row):
    vocabulary = legacy_roles()
    result = {}
    for key, value in row.items():
        if isinstance(value, str):
            if key in ("role", "team", "win", "winner", "expected", "answer"):
                value = vocabulary.get(value, value)
            elif key == "roles":
                value = " ".join(vocabulary.get(role, role) for role in value.split())
            elif key in ("case", "source", "game"):
                value = current_id(value)
        name, separator, suffix = key.partition("_")
        result[vocabulary.get(name, name) + separator + suffix] = value
    return result


def csv_rows(handle):
    return map(current_row, csv.DictReader(handle))


def json_rows(path):
    return [current_row(json.loads(line)) for line in path.read_text().splitlines()]
