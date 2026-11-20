"""Render the experimental team vocabulary at the model boundary."""

import json
import re

COLORS = {"good": "Blue", "bad": "Red"}


def color_prose(text):
    def name(match):
        word = match[0]
        color = COLORS[word.lower()]
        return color.upper() if word.isupper() else color

    # The final sentence of the construction guide uses "good" as an adjective.
    text = text.replace("A good forward build", "A productive forward build")
    return re.sub(r"\b(good|bad)\b", name, text, flags=re.IGNORECASE)


def color_brief(body):
    """Relabel referee-authored information. Preserve speech, evidence, and legal option values."""
    system, user = body["messages"]
    system["content"] = color_prose(system["content"])
    context = json.loads(user["content"])
    for field in ("common_knowledge", "private_role_card"):
        if field in context:
            context[field] = color_prose(context[field])
    for field in ("role", "your_role", "your_team"):
        if field in context:
            context[field] = COLORS[context[field]]
    private = context["your_private_role_information"]
    private["alignment"] = COLORS[private["alignment"]]

    def renamed_fields(fields):
        return {k.replace("bad", "red").replace("good", "blue"): v for k, v in fields.items()}

    context["your_private_role_information"] = renamed_fields(private)
    user["content"] = json.dumps(renamed_fields(context), separators=(",", ":"))
