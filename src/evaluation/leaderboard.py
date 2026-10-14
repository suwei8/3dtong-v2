from collections import defaultdict


def update_score(records):
    table = defaultdict(lambda: {"hit": 0, "total": 0})
    for item in records:
        name = item["model"]
        table[name]["total"] += 1
        table[name]["hit"] += int(item.get("hit", False))
    for value in table.values():
        value["rate"] = value["hit"] / value["total"] if value["total"] else 0
    return dict(table)
