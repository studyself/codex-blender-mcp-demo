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
MATCAP_TEXTURE = ROOT / "assets" / "matcaps" / "1D3FCC_051B5F_81A0F2_5579E9-256px.png"
OUT_DIR = ROOT / "outputs" / "matcap_bust_components"
PART_DIR = OUT_DIR / "parts"
SUMMARY_PATH = OUT_DIR / "component_summary.json"
CONTACT_SHEET = OUT_DIR / "component_contact_sheet.png"


def blender_script() -> str:
    return dedent(
        f"""
        import json
        import math
        from pathlib import Path

        import bpy
        from mathutils import Vector

        out_dir = Path(r"{OUT_DIR}")
        part_dir = Path(r"{PART_DIR}")
        summary_path = Path(r"{SUMMARY_PATH}")
        matcap_texture = Path(r"{MATCAP_TEXTURE}")
        part_dir.mkdir(parents=True, exist_ok=True)
        for old in part_dir.glob("component_*.png"):
            old.unlink()

        scene = bpy.context.scene
        scene.frame_set(1)
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        scene.render.film_transparent = False
        scene.render.image_settings.file_format = "PNG"
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except Exception:
            scene.render.engine = "BLENDER_EEVEE"
        try:
            scene.eevee.taa_render_samples = 32
        except Exception:
            pass

        world = scene.world or bpy.data.worlds.new("World")
        scene.world = world
        world.color = (0.018, 0.02, 0.028)

        # Apply a visible MatCap texture from nidorx/matcaps to the preview material.
        mat = bpy.data.materials.get("Material")
        if mat and mat.use_nodes:
            image = bpy.data.images.load(str(matcap_texture))
            try:
                image.colorspace_settings.name = "sRGB"
            except Exception:
                pass
            node = mat.node_tree.nodes.get("SolidTexture")
            if node and hasattr(node, "image"):
                node.image = image

        # Remove unrelated preview meshes so only the bust split is rendered.
        for name in ["PreviewSolidBall", "PreviewSolidSuzanne"]:
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)

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
        for idx, obj in enumerate(parts, start=1):
            obj.name = f"component_{{idx:03d}}_v{{len(obj.data.vertices):06d}}"

        # Hide everything except camera/lights; each component is rendered alone.
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                obj.hide_render = True
                obj.hide_viewport = True

        # Add a simple orthographic camera and two soft lights for consistent thumbnails.
        cam = bpy.data.objects.get("ComponentCamera")
        if cam is None:
            bpy.ops.object.camera_add(location=(3.4, -4.2, 2.6))
            cam = bpy.context.object
            cam.name = "ComponentCamera"
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 1.0
        scene.camera = cam

        bpy.ops.object.light_add(type="AREA", location=(0.0, -3.2, 3.2))
        key = bpy.context.object
        key.name = "ComponentKeyLight"
        key.data.energy = 360
        key.data.size = 4.0
        bpy.ops.object.light_add(type="POINT", location=(-2.4, 1.8, 2.3))
        rim = bpy.context.object
        rim.name = "ComponentRimLight"
        rim.data.energy = 120
        rim.data.color = (0.2, 0.7, 1.0)

        def bounds_for(obj):
            coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            min_v = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
            max_v = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
            return min_v, max_v, (min_v + max_v) / 2

        def aim_camera_at(obj):
            min_v, max_v, center = bounds_for(obj)
            dims = max_v - min_v
            size = max(dims.x, dims.y, dims.z, 0.08)
            cam.data.ortho_scale = size * 1.45
            loc = center + Vector((size * 1.6, -size * 2.2, size * 1.45))
            cam.location = loc
            direction = center - loc
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
            return dims, center, size

        summary = []
        for idx, obj in enumerate(parts, start=1):
            obj.hide_render = False
            obj.hide_viewport = False
            dims, center, size = aim_camera_at(obj)
            png_path = part_dir / f"component_{{idx:03d}}.png"
            scene.render.filepath = str(png_path)
            bpy.ops.render.render(write_still=True)
            summary.append({{
                "index": idx,
                "object": obj.name,
                "vertices": len(obj.data.vertices),
                "faces": len(obj.data.polygons),
                "dimensions": [round(dims.x, 5), round(dims.y, 5), round(dims.z, 5)],
                "center": [round(center.x, 5), round(center.y, 5), round(center.z, 5)],
                "image": str(png_path),
            }})
            obj.hide_render = True
            obj.hide_viewport = True

        payload = {{
            "source": "nidorx/matcaps scene.blend",
            "source_object": "PreviewSolideFemaleSCIFIbust",
            "component_count": len(parts),
            "matcap_texture": str(matcap_texture),
            "parts": summary,
        }}
        summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print("__BUST_COMPONENT_EXPORT_START__")
        print(json.dumps({{"component_count": len(parts), "summary": str(summary_path)}}, ensure_ascii=False))
        print("__BUST_COMPONENT_EXPORT_END__")
        """
    )


def make_contact_sheet() -> dict:
    part_images = sorted(PART_DIR.glob("component_*.png"))
    if not part_images:
        return {"ok": False, "error": "No component images found"}

    thumb_size = 128
    label_h = 28
    cols = 10
    rows = (len(part_images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_size, rows * (thumb_size + label_h)), (18, 20, 26))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()

    for idx, path in enumerate(part_images):
        im = Image.open(path).convert("RGB")
        im.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
        x = (idx % cols) * thumb_size
        y = (idx // cols) * (thumb_size + label_h)
        px = x + (thumb_size - im.width) // 2
        py = y + (thumb_size - im.height) // 2
        sheet.paste(im, (px, py))
        draw.text((x + 6, y + thumb_size + 6), path.stem.replace("component_", "#"), fill=(230, 236, 244), font=font)

    sheet.save(CONTACT_SHEET)
    return {
        "ok": True,
        "contact_sheet": str(CONTACT_SHEET),
        "component_images": len(part_images),
        "size": sheet.size,
    }


def run_blender(blender_path: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = OUT_DIR / "_export_components_in_blender.py"
    script_path.write_text(blender_script(), encoding="utf-8")

    command = [
        blender_path,
        "--background",
        str(SOURCE_BLEND),
        "--python",
        str(script_path),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", default=DEFAULT_BLENDER)
    args = parser.parse_args()

    if not SOURCE_BLEND.exists():
        print(f"Missing source blend: {SOURCE_BLEND}")
        return 1
    if not MATCAP_TEXTURE.exists():
        print(f"Missing matcap texture: {MATCAP_TEXTURE}")
        return 1

    code = run_blender(args.blender)
    if code != 0:
        return code
    result = make_contact_sheet()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
