#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.detect import detect
from graphify.export import to_html
from graphify.report import generate
from graphify.watch import _git_head


REPO_ROOT = Path(__file__).resolve().parents[1]


CONFIGS = [
    {
        "target": Path("."),
        "out": Path("graphify-out"),
        "root_label": "Software-Engineering",
        "labels": {
            0: "Gesture Runtime Lifecycle",
            1: "Config Persistence & Database",
            2: "Realtime & Multimodal Services",
            3: "Gesture Detection & Push Logic",
            4: "Frontend Interaction Layout",
            5: "Calibration Analysis & Apply",
            6: "Voice Runtime",
            7: "Gesture Tracking Pipeline",
            8: "Sequence Matching",
            9: "Frontend Realtime Client",
            10: "Gesture Contracts",
        },
    },
    {
        "target": Path("Backend"),
        "out": Path("Backend/graphify-out"),
        "root_label": "Backend",
        "labels": {
            0: "Gesture Runtime Lifecycle",
            1: "Gesture Detection & Push Logic",
            2: "Config Persistence & Database",
            3: "Realtime & Multimodal Services",
            4: "Calibration Analysis & Apply",
            5: "Voice Runtime",
            6: "Gesture Resolver & Contracts",
            7: "Sequence Matching",
        },
    },
    {
        "target": Path("Frontend/nimrag-frontend"),
        "out": Path("Frontend/nimrag-frontend/graphify-out"),
        "root_label": "Frontend/nimrag-frontend",
        "labels": {
            0: "Layout Rendering Helpers",
            1: "Widget Mutation & Targeting",
            2: "Widget Registry & Normalization",
            3: "Realtime Client",
            4: "Module Manager Shell",
            5: "Layout Placement & Upsert",
            6: "Grid Positioning & Moves",
            7: "Focus State & Arrange Entry",
            8: "Focus Exit & Reducer Flow",
            9: "Focused Widget Lookup",
        },
    },
]


def main() -> int:
    for config in CONFIGS:
        out_dir = REPO_ROOT / config["out"]
        graph_json = out_dir / "graph.json"
        if not graph_json.exists():
            raise FileNotFoundError(f"Missing graph file: {graph_json}")

        raw = json.loads(graph_json.read_text(encoding="utf-8"))
        graph = build_from_json(raw)
        communities = defaultdict(list)
        for node in raw.get("nodes", []):
            communities[int(node.get("community", -1))].append(node["id"])
        communities = dict(sorted(communities.items()))

        labels = config["labels"]
        cohesion = score_all(graph, communities)
        gods = god_nodes(graph)
        surprises = surprising_connections(graph, communities)
        questions = suggest_questions(graph, communities, labels)
        detection_result = detect(REPO_ROOT / config["target"])
        detection_result.pop("warning", None)
        report = generate(
            graph,
            communities,
            cohesion,
            labels,
            gods,
            surprises,
            detection_result,
            {"input": 0, "output": 0},
            config["root_label"],
            suggested_questions=questions,
            built_at_commit=_git_head(),
        )

        (out_dir / ".graphify_labels.json").write_text(
            json.dumps({str(key): value for key, value in labels.items()}, indent=2),
            encoding="utf-8",
        )
        (out_dir / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
        to_html(graph, communities, str(out_dir / "graph.html"), community_labels=labels)
        print(f"Applied labels to {config['root_label']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())