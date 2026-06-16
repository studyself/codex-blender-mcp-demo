from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
SOURCE_BLEND = ROOT / "assets" / "nidorx_matcaps_scene" / "scene.blend"
OUT_DIR = ROOT / "outputs" / "matcap_bust_component001_semantic"
REGION_DIR = OUT_DIR / "regions"
SUMMARY_PATH = OUT_DIR / "component001_semantic_segmentation_summary.json"
CONTACT_SHEET = OUT_DIR / "component001_semantic_regions_contact_sheet.png"


def blender_script() -> str:
    return dedent(
        f"""
        import json
        import math
        from pathlib import Path

        import bpy
        from mathutils import Vector

        out_dir = Path(r"{OUT_DIR}")
        region_dir = Path(r"{REGION_DIR}")
        summary_path = Path(r"{SUMMARY_PATH}")
        out_dir.mkdir(parents=True, exist_ok=True)
        region_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("component001_semantic_*.png"):
            old.unlink()
        for old in region_dir.glob("semantic_region_*.png"):
            old.unlink()

        scene = bpy.context.scene
        scene.frame_set(1)
        scene.render.resolution_x = 1500
        scene.render.resolution_y = 1100
        scene.render.film_transparent = False
        scene.render.image_settings.file_format = "PNG"
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except Exception:
            scene.render.engine = "BLENDER_EEVEE"
        try:
            scene.eevee.taa_render_samples = 64
        except Exception:
            pass

        world = scene.world or bpy.data.worlds.new("World")
        scene.world = world
        world.color = (0.008, 0.01, 0.016)

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
        main.name = "component_001_main_continuous_mesh"

        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj != main:
                obj.hide_render = True
                obj.hide_viewport = True

        mesh = main.data
        mesh.update()
        local_vertices = [v.co.copy() for v in mesh.vertices]
        world_vertices = [main.matrix_world @ v for v in local_vertices]
        min_x = min(v.x for v in world_vertices); max_x = max(v.x for v in world_vertices)
        min_y = min(v.y for v in world_vertices); max_y = max(v.y for v in world_vertices)
        min_z = min(v.z for v in world_vertices); max_z = max(v.z for v in world_vertices)
        min_lx = min(v.x for v in local_vertices); max_lx = max(v.x for v in local_vertices)
        min_lz = min(v.z for v in local_vertices); max_lz = max(v.z for v in local_vertices)
        center = Vector(((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2))

        def clamp01(value):
            return max(0.0, min(1.0, value))

        def height_t(world_point):
            return clamp01((world_point.z - min_z) / max(max_z - min_z, 1e-6))

        # Local Z maps to the face/back direction in this source file. The previous
        # preview used it as height, which caused vertical color bands.
        def front_t(local_point):
            return clamp01((local_point.z - min_lz) / max(max_lz - min_lz, 1e-6))

        def side_t(local_point):
            return clamp01((local_point.x - min_lx) / max(max_lx - min_lx, 1e-6))

        regions = [
            {{
                "name": "cranial_shell",
                "label": "cranial shell",
                "color": (0.16, 0.45, 1.00, 1),
                "offset": (0.00, 0.08, 0.28),
            }},
            {{
                "name": "face_mask",
                "label": "face mask",
                "color": (0.86, 0.92, 1.00, 1),
                "offset": (0.34, 0.24, 0.06),
            }},
            {{
                "name": "jaw_neck_front",
                "label": "jaw + front neck",
                "color": (0.18, 0.95, 0.82, 1),
                "offset": (0.24, 0.18, -0.02),
            }},
            {{
                "name": "rear_head_plate",
                "label": "rear head plate",
                "color": (0.46, 0.62, 1.00, 1),
                "offset": (-0.18, -0.24, 0.12),
            }},
            {{
                "name": "temple_ear_module",
                "label": "temple / ear module",
                "color": (0.96, 0.32, 0.72, 1),
                "offset": (-0.05, 0.32, 0.06),
            }},
            {{
                "name": "neck_spine",
                "label": "neck spine",
                "color": (1.00, 0.58, 0.20, 1),
                "offset": (-0.18, -0.28, -0.02),
            }},
            {{
                "name": "upper_chest_shell",
                "label": "upper chest shell",
                "color": (0.22, 0.78, 1.00, 1),
                "offset": (0.22, 0.18, -0.12),
            }},
            {{
                "name": "front_bust_pod",
                "label": "front bust pod",
                "color": (1.00, 0.30, 0.24, 1),
                "offset": (0.36, 0.26, -0.22),
            }},
            {{
                "name": "side_rib_panel",
                "label": "side rib panel",
                "color": (0.68, 1.00, 0.28, 1),
                "offset": (0.04, 0.34, -0.12),
            }},
            {{
                "name": "rear_torso_shell",
                "label": "rear torso shell",
                "color": (0.76, 0.48, 1.00, 1),
                "offset": (-0.26, -0.30, -0.16),
            }},
            {{
                "name": "lower_base_block",
                "label": "lower base block",
                "color": (0.94, 0.86, 0.62, 1),
                "offset": (-0.08, -0.04, -0.34),
            }},
            {{
                "name": "connector_transition",
                "label": "connector transition",
                "color": (0.78, 0.84, 0.92, 1),
                "offset": (0.00, 0.00, -0.24),
            }},
        ]

        def assign_region(local_center, world_center, normal):
            h = height_t(world_center)
            f = front_t(local_center)
            s = side_t(local_center)

            if h > 0.73 and f > 0.64:
                return 1  # face mask / forehead front
            if h > 0.71:
                return 0  # skull shell
            if h > 0.58 and f < 0.42:
                return 3  # rear head
            if h > 0.56 and 0.38 <= f <= 0.72 and (s < 0.34 or s > 0.66):
                return 4  # temple/ear band
            if h > 0.55 and f >= 0.58:
                return 1  # face mask

            if 0.39 < h <= 0.62 and f >= 0.58:
                return 2  # jaw/front neck
            if 0.34 < h <= 0.65 and f < 0.48:
                return 5  # rear neck/spine

            if h <= 0.18:
                return 10 if f < 0.58 else 11
            if 0.18 < h <= 0.34 and f >= 0.63:
                return 7  # front bust pod
            if 0.18 < h <= 0.44 and f < 0.47:
                return 9  # rear torso
            if 0.25 < h <= 0.52 and (s < 0.27 or s > 0.73):
                return 8  # side rib panel
            if 0.31 < h <= 0.52 and f >= 0.50:
                return 6  # upper chest shell
            if f < 0.50:
                return 9
            return 6

        region_faces = [[] for _ in regions]
        face_counts = [0 for _ in regions]
        for poly in mesh.polygons:
            local_center = sum((mesh.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
            world_center = main.matrix_world @ local_center
            region_idx = assign_region(local_center, world_center, poly.normal)
            region_faces[region_idx].append(tuple(poly.vertices))
            face_counts[region_idx] += 1

        def make_material(name, color, strength=0.72):
            mat = bpy.data.materials.new("semantic_" + name)
            mat.diffuse_color = color
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            nodes.clear()
            output = nodes.new("ShaderNodeOutputMaterial")
            principled = nodes.new("ShaderNodeBsdfPrincipled")
            if "Base Color" in principled.inputs:
                principled.inputs["Base Color"].default_value = color
            if "Roughness" in principled.inputs:
                principled.inputs["Roughness"].default_value = 0.46
            if "Metallic" in principled.inputs:
                principled.inputs["Metallic"].default_value = 0.12
            if "Emission Color" in principled.inputs:
                principled.inputs["Emission Color"].default_value = color
            if "Emission Strength" in principled.inputs:
                principled.inputs["Emission Strength"].default_value = strength
            mat.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
            return mat

        main.hide_render = True
        main.hide_viewport = True
        region_objects = []
        for idx, (region, faces) in enumerate(zip(regions, region_faces), start=1):
            used = []
            used_set = set()
            for face in faces:
                for vertex_index in face:
                    if vertex_index not in used_set:
                        used_set.add(vertex_index)
                        used.append(vertex_index)
            index_map = {{old: new for new, old in enumerate(used)}}
            verts_new = [local_vertices[old] for old in used]
            faces_new = [tuple(index_map[vertex_index] for vertex_index in face) for face in faces]
            mesh_new = bpy.data.meshes.new(f"semantic_mesh_{{idx:02d}}_{{region['name']}}")
            mesh_new.from_pydata(verts_new, [], faces_new)
            mesh_new.update()
            obj_new = bpy.data.objects.new(f"semantic_region_{{idx:02d}}_{{region['name']}}", mesh_new)
            obj_new.matrix_world = main.matrix_world.copy()
            bpy.context.collection.objects.link(obj_new)
            obj_new.data.materials.append(make_material(region["name"], region["color"]))
            obj_new["semantic_label"] = region["label"]
            obj_new["explode_offset"] = region["offset"]
            region_objects.append(obj_new)

        def make_text_material():
            mat = bpy.data.materials.new("semantic_label_white")
            mat.diffuse_color = (0.92, 0.98, 1.0, 1)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                if "Base Color" in bsdf.inputs:
                    bsdf.inputs["Base Color"].default_value = (0.92, 0.98, 1.0, 1)
                if "Emission Color" in bsdf.inputs:
                    bsdf.inputs["Emission Color"].default_value = (0.92, 0.98, 1.0, 1)
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = 0.35
            return mat

        label_mat = make_text_material()
        legend_objects = []
        for idx, region in enumerate(regions, start=1):
            bpy.ops.object.text_add(location=(min_x - 0.45, min_y - 0.82, max_z - 0.10 - idx * 0.105), rotation=(math.radians(68), 0, math.radians(-5)))
            txt = bpy.context.object
            txt.name = f"semantic_legend_{{idx:02d}}"
            txt.data.body = f"{{idx:02d}} {{region['label']}}"
            txt.data.align_x = "LEFT"
            txt.data.align_y = "CENTER"
            txt.data.size = 0.045
            txt.data.materials.append(label_mat)
            legend_objects.append(txt)

        bpy.ops.object.light_add(type="AREA", location=(center.x + 0.2, center.y - 3.8, center.z + 3.1))
        key = bpy.context.object
        key.name = "semantic_key_light"
        key.data.energy = 520
        key.data.size = 4.6
        bpy.ops.object.light_add(type="POINT", location=(center.x - 2.5, center.y + 1.8, center.z + 1.7))
        rim = bpy.context.object
        rim.name = "semantic_rim_light"
        rim.data.energy = 170
        rim.data.color = (0.20, 0.75, 1.0)

        cam = bpy.data.objects.get("SemanticSegmentationCamera")
        if cam is None:
            bpy.ops.object.camera_add()
            cam = bpy.context.object
            cam.name = "SemanticSegmentationCamera"
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 2.75
        scene.camera = cam

        def set_camera(location, target):
            cam.location = Vector(location)
            direction = Vector(target) - cam.location
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

        base_locations = [obj.location.copy() for obj in region_objects]
        for legend in legend_objects:
            legend.hide_render = True
            legend.hide_viewport = True

        def render_named(name, exploded):
            for obj, base_location, region in zip(region_objects, base_locations, regions):
                obj.location = base_location.copy()
                if exploded:
                    obj.location = base_location + Vector(region["offset"]) * 0.62
            set_camera((center.x + 2.85, center.y - 3.55, center.z + 1.55), (center.x, center.y, center.z + 0.08))
            cam.data.ortho_scale = 3.05 if not exploded else 3.35
            scene.render.filepath = str(out_dir / f"component001_semantic_{{name}}.png")
            bpy.ops.render.render(write_still=True)

        render_named("assembled_preview", exploded=False)
        render_named("micro_exploded_preview", exploded=True)

        # Render one thumbnail per semantic module.
        for obj, base_location in zip(region_objects, base_locations):
            obj.hide_render = True
            obj.hide_viewport = True
            obj.location = base_location.copy()
        for obj in legend_objects:
            obj.hide_render = True
            obj.hide_viewport = True

        def bounds_for(obj):
            coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            min_v = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
            max_v = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
            return min_v, max_v, (min_v + max_v) / 2

        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        for idx, obj in enumerate(region_objects, start=1):
            obj.hide_render = False
            obj.hide_viewport = False
            obj.location = base_locations[idx - 1].copy()
            min_v, max_v, obj_center = bounds_for(obj)
            dims = max_v - min_v
            size = max(dims.x, dims.y, dims.z, 0.08)
            cam.data.ortho_scale = size * 1.65
            set_camera((obj_center.x + size * 1.65, obj_center.y - size * 2.25, obj_center.z + size * 1.35), obj_center)
            scene.render.filepath = str(region_dir / f"semantic_region_{{idx:02d}}_{{regions[idx - 1]['name']}}.png")
            bpy.ops.render.render(write_still=True)
            obj.hide_render = True
            obj.hide_viewport = True

        summary = {{
            "source": "nidorx/matcaps scene.blend",
            "source_object": "PreviewSolideFemaleSCIFIbust",
            "component": "component_001, largest continuous loose mesh",
            "vertices": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "method": "world-coordinate semantic segmentation of a continuous mesh; not original authored loose components",
            "regions": [
                {{
                    "index": idx,
                    "name": region["name"],
                    "label": region["label"],
                    "face_count": face_counts[idx - 1],
                    "image": str(region_dir / f"semantic_region_{{idx:02d}}_{{region['name']}}.png"),
                }}
                for idx, region in enumerate(regions, start=1)
            ],
            "images": {{
                "assembled_preview": str(out_dir / "component001_semantic_assembled_preview.png"),
                "micro_exploded_preview": str(out_dir / "component001_semantic_micro_exploded_preview.png"),
            }},
        }}
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print("__COMPONENT001_SEMANTIC_SEGMENTATION_START__")
        print(json.dumps(summary, ensure_ascii=False))
        print("__COMPONENT001_SEMANTIC_SEGMENTATION_END__")
        """
    )


def make_contact_sheet() -> dict:
    images = sorted(REGION_DIR.glob("semantic_region_*.png"))
    if not images:
        return {"ok": False, "error": "No semantic region images found"}

    thumb = 180
    label_h = 34
    cols = 4
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + label_h)), (12, 14, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    for idx, path in enumerate(images):
        im = Image.open(path).convert("RGB")
        im.thumbnail((thumb, thumb), Image.Resampling.LANCZOS)
        x = (idx % cols) * thumb
        y = (idx // cols) * (thumb + label_h)
        px = x + (thumb - im.width) // 2
        py = y + (thumb - im.height) // 2
        sheet.paste(im, (px, py))
        label = path.stem.replace("semantic_region_", "#").replace("_", " ")
        draw.text((x + 8, y + thumb + 8), label[:26], fill=(232, 238, 248), font=font)

    sheet.save(CONTACT_SHEET)
    return {"ok": True, "contact_sheet": str(CONTACT_SHEET), "region_images": len(images)}


def run_blender(blender_path: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = OUT_DIR / "_preview_component001_semantic_segmentation.py"
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

    code = run_blender(args.blender)
    if code != 0:
        return code
    print(json.dumps(make_contact_sheet(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
