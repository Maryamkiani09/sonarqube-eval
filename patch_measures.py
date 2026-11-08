import re

p = r"src\sonar_tools\measures.py"
s = open(p, encoding="utf-8").read()

new = '''def history(client: SonarClient, project: str, metrics: list[str], from_date: str | None = None) -> dict[str, list[tuple[str, float]]]:
    """metric -> [(date, value), ...] oldest first."""
    params = {"component": project, "metrics": ",".join(metrics)}
    if from_date:
        params["from"] = from_date
    body = client.get("api/measures/search_history", **params)
    out: dict[str, list[tuple[str, float]]] = {}
    for item in body.get("measures", []):
        points = [(h["date"], float(h["value"])) for h in item.get("history", []) if "value" in h]
        out[item["metric"]] = points
    return out


def trend('''

s2 = re.sub(r"(?s)def history\(.*?\n\ndef trend\(", new, s, count=1)
open(p, "w", encoding="utf-8", newline="").write(s2)
print("patched" if s2 != s else "NO CHANGE")
