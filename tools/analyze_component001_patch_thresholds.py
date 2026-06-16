from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
SOURCE_BLEND = ROOT / "assets" / "nidorx_matcaps_scene" / "scene.blend"
OUT_DIR = ROOT / "outputs" / "matcap_bust_component001_patches"
SUMMARY_PATH = OUT_DIR / "component001_patch_thresholds.json"


def blender_script() -> str:
    return dedent(
        f"""
        import json
        import math
        from collections import deque
        from pathlib import Path

        import bpy

        out_dir = Path(r"{OUT_DIR}")
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = Path(r"{SUMMARY_PATH}")

        bust = bpy.data.objects.get("PreviewSolideFemaleSCIFIbust")
        if bust is None:
            raise RuntimeError("PreviewSolideFemaleSCIFIbust not found")

        bpy.ops.object.select_all(action="DESELECT")
        bust.select_set(True)
        bpy.context.view_layer.objects.active = bust
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.separate(type="LOOSE")
        bpy.ops.object.mode_set(mode="OBJECT")

        parts = [
            obj for obj in bpy.data.objects
            if obj.type == "MESH" and obj.name.startswith("PreviewSolideFemaleSCIFIbust")
        ]
        parts.sort(key=lambda obj: len(obj.data.vertices), reverse=True)
        main = parts[0]
        mesh = main.data
        mesh.update()

        edge_faces = {{}}
        for poly in mesh.polygons:
            for edge_key in poly.edge_keys:
                edge_faces.setdefault(tuple(edge_key), []).append(poly.index)

        shared_edges = [
            tuple(faces)
            for faces in edge_faces.values()
            if len(faces) == 2
        ]
        normals = [poly.normal.copy() for poly in mesh.polygons]

        def patch_sizes_for(threshold_deg):
            threshold = math.radians(threshold_deg)
            adjacency = [[] for _ in mesh.polygons]
            sharp_edges = 0
            for a, b in shared_edges:
                angle = normals[a].angle(normals[b], 0.0)
                if angle <= threshold:
                    adjacency[a].append(b)
                    adjacency[b].append(a)
                else:
                    sharp_edges += 1

            visited = bytearray(len(mesh.polygons))
            sizes = []
            for start in range(len(mesh.polygons)):
                if visited[start]:
                    continue
                visited[start] = 1
                queue = deque([start])
                count = 0
                while queue:
                    face = queue.popleft()
                    count += 1
                    for other in adjacency[face]:
                        if not visited[other]:
                            visited[other] = 1
                            queue.append(other)
                sizes.append(count)
            sizes.sort(reverse=True)
            return {{
                "threshold_degrees": threshold_deg,
                "patch_count": len(sizes),
                "sharp_edge_count": sharp_edges,
                "patches_over_50_faces": sum(1 for size in sizes if size >= 50),
                "patches_over_200_faces": sum(1 for size in sizes if size >= 200),
                "patches_over_1000_faces": sum(1 for size in sizes if size >= 1000),
                "largest_20_face_counts": sizes[:20],
            }}

        payload = {{
            "source_object": "PreviewSolideFemaleSCIFIbust",
            "component": "largest loose component / component_001",
            "vertices": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "thresholds": [patch_sizes_for(deg) for deg in [18, 24, 30, 36, 42, 50, 60]],
        }}
        summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print("__PATCH_THRESHOLDS_START__")
        print(json.dumps(payload, ensure_ascii=False))
        print("__PATCH_THRESHOLDS_END__")
        """
    )


def run_blender(blender_path: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = OUT_DIR / "_analyze_component001_patch_thresholds.py"
    script_path.write_text(blender_script(), encoding="utf-8")
    command = [
        blender_path,
        "--background",
        str(SOURCE_BLEND),
        "--python",
        str(script_path),
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", default=DEFAULT_BLENDER)
    args = parser.parse_args()
    if not SOURCE_BLEND.exists():
        print(f"Missing source blend: {SOURCE_BLEND}")
        return 1
    return run_blender(args.blender)


if __name__ == "__main__":
    raise SystemExit(main())
