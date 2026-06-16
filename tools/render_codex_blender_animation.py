from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
BLENDER_PATH = os.environ.get(
    "BLENDER_PATH",
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
)
CASE_DIR = ROOT / "outputs" / "codex_blender_case"
BLEND_PATH = CASE_DIR / "codex_blender_mcp_case.blend"
ANIM_BLEND_PATH = CASE_DIR / "codex_blender_mcp_case_animated.blend"
MP4_PATH = CASE_DIR / "codex_blender_mcp_case_animation.mp4"
GIF_PATH = CASE_DIR / "codex_blender_mcp_case_animation.gif"
SUMMARY_PATH = CASE_DIR / "codex_blender_mcp_animation_summary.json"
FRAME_DIR = CASE_DIR / "animation_frames"


def blender_source() -> str:
    source = dedent(
        """
        import json
        import math
        from pathlib import Path

        import bpy
        from mathutils import Vector

        anim_blend_path = Path(__ANIM_BLEND_PATH__)
        mp4_path = Path(__MP4_PATH__)
        gif_path = Path(__GIF_PATH__)
        frame_dir = Path(__FRAME_DIR__)
        frame_dir.mkdir(parents=True, exist_ok=True)
        for old_frame in frame_dir.glob("frame_*.png"):
            old_frame.unlink()

        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = 48
        scene.frame_current = 1
        scene.render.resolution_x = 800
        scene.render.resolution_y = 450
        scene.render.fps = 24
        scene.render.film_transparent = False

        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except Exception:
            scene.render.engine = "BLENDER_EEVEE"
        try:
            scene.eevee.taa_render_samples = 16
        except Exception:
            pass

        def material(name, color, emission_strength=0.0):
            mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                if "Base Color" in bsdf.inputs:
                    bsdf.inputs["Base Color"].default_value = color
                if "Emission Color" in bsdf.inputs:
                    bsdf.inputs["Emission Color"].default_value = color
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = emission_strength
            return mat

        pulse_mat = material("mat_animation_pulse", (0.18, 1.0, 0.72, 1), 2.5)
        orange_mat = bpy.data.materials.get("mat_codex_orange") or material("mat_codex_orange", (1.0, 0.42, 0.18, 1), 1.3)
        cyan_mat = bpy.data.materials.get("mat_panel_edge") or material("mat_panel_edge", (0.03, 0.85, 0.95, 1), 1.3)

        # Clear prior animation preview helper objects if rerun.
        for obj in list(bpy.data.objects):
            if obj.name.startswith("anim_"):
                bpy.data.objects.remove(obj, do_unlink=True)

        def cube(name, loc, scale, mat):
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
            obj = bpy.context.object
            obj.name = name
            obj.scale = scale
            obj.data.materials.append(mat)
            return obj

        def sphere(name, loc, radius, mat):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=radius, location=loc)
            obj = bpy.context.object
            obj.name = name
            obj.data.materials.append(mat)
            return obj

        def add_key(obj, frame, location=None, rotation=None, scale=None):
            scene.frame_set(frame)
            if location is not None:
                obj.location = location
                obj.keyframe_insert(data_path="location", frame=frame)
            if rotation is not None:
                obj.rotation_euler = rotation
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            if scale is not None:
                obj.scale = scale
                obj.keyframe_insert(data_path="scale", frame=frame)

        # Add visible markers to the otherwise symmetric MCP core rotation.
        core = bpy.data.objects.get("mcp_core")
        if core is not None:
            core.rotation_euler = (0, 0, 0)
            core.keyframe_insert(data_path="rotation_euler", frame=1)
            core.rotation_euler = (0, 0, math.radians(360))
            core.keyframe_insert(data_path="rotation_euler", frame=48)

            for idx, z in enumerate([1.0, 1.45, 1.9]):
                marker = cube(f"anim_mcp_rotor_marker_{idx}", (0.43, 0.1, z), (0.055, 0.08, 0.18), orange_mat)
                marker.parent = core
                marker.matrix_parent_inverse = core.matrix_world.inverted()

        # Pulses show instruction flow: prompt -> MCP -> generated asset.
        p1 = sphere("anim_pulse_prompt_to_mcp", (-1.85, 0.0, 1.57), 0.11, pulse_mat)
        add_key(p1, 1, location=(-1.85, 0.0, 1.57), scale=(0.7, 0.7, 0.7))
        add_key(p1, 24, location=(-0.55, 0.02, 1.57), scale=(1.15, 1.15, 1.15))
        add_key(p1, 32, location=(-1.85, 0.0, 1.57), scale=(0.7, 0.7, 0.7))
        add_key(p1, 48, location=(-0.55, 0.02, 1.57), scale=(1.15, 1.15, 1.15))

        p2 = sphere("anim_pulse_mcp_to_asset", (0.58, 0.05, 1.57), 0.12, cyan_mat)
        add_key(p2, 1, location=(0.58, 0.05, 1.57), scale=(0.65, 0.65, 0.65))
        add_key(p2, 24, location=(2.1, 0.05, 1.57), scale=(1.2, 1.2, 1.2))
        add_key(p2, 48, location=(0.58, 0.05, 1.57), scale=(0.65, 0.65, 0.65))

        # Make rover arm visibly wave.
        for name, start_z, end_z in [
            ("rover_arm_1", math.radians(-18), math.radians(20)),
            ("rover_arm_2", math.radians(20), math.radians(-24)),
            ("rover_gripper", math.radians(-10), math.radians(28)),
        ]:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            base = obj.rotation_euler.copy()
            add_key(obj, 1, rotation=(base.x, base.y, start_z))
            add_key(obj, 24, rotation=(base.x, base.y, end_z))
            add_key(obj, 48, rotation=(base.x, base.y, start_z))

        # Gentle camera move, so the video feels alive even at low render cost.
        cam = scene.camera
        if cam is not None:
            base_loc = Vector(cam.location)
            base_rot = cam.rotation_euler.copy()
            add_key(cam, 1, location=base_loc, rotation=base_rot)
            add_key(cam, 24, location=base_loc + Vector((-0.35, 0.28, 0.08)), rotation=(base_rot.x + math.radians(0.8), base_rot.y, base_rot.z - math.radians(1.8)))
            add_key(cam, 48, location=base_loc, rotation=base_rot)

        # Save animated .blend first so it can be opened and played in Blender UI.
        bpy.ops.wm.save_as_mainfile(filepath=str(anim_blend_path))

        # Render a PNG frame sequence; the driver script assembles a GIF.
        scene.render.filepath = str(frame_dir / "frame_")
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(animation=True)

        summary = {
            "animated_blend_path": str(anim_blend_path),
            "mp4_path": str(mp4_path),
            "gif_path": str(gif_path),
            "frame_dir": str(frame_dir),
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "fps": scene.render.fps,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "object_count": len(bpy.data.objects),
            "engine": scene.render.engine,
        }
        print("__CODEX_BLENDER_ANIMATION_START__")
        print(json.dumps(summary, ensure_ascii=False))
        print("__CODEX_BLENDER_ANIMATION_END__")
        """
    )
    return (
        source.replace("__ANIM_BLEND_PATH__", repr(str(ANIM_BLEND_PATH)))
        .replace("__MP4_PATH__", repr(str(MP4_PATH)))
        .replace("__GIF_PATH__", repr(str(GIF_PATH)))
        .replace("__FRAME_DIR__", repr(str(FRAME_DIR)))
    )


def make_gif() -> dict:
    from PIL import Image, ImageSequence

    frames = sorted(FRAME_DIR.glob("frame_*.png"))
    if not frames:
        return {"ok": False, "error": "No PNG frames were rendered.", "frame_dir": str(FRAME_DIR)}

    images = []
    for frame in frames:
        with Image.open(frame) as im:
            images.append(im.convert("P", palette=Image.Palette.ADAPTIVE, colors=128).copy())

    first, rest = images[0], images[1:]
    first.save(
        GIF_PATH,
        save_all=True,
        append_images=rest,
        duration=42,
        loop=0,
        optimize=True,
    )
    return {
        "ok": True,
        "gif_path": str(GIF_PATH),
        "frame_count": len(frames),
        "size": Image.open(frames[0]).size,
    }


def main() -> int:
    if not BLEND_PATH.exists():
        print(f"Missing source blend file: {BLEND_PATH}")
        return 1

    os.environ["BLENDER_MCP_MODE"] = "subprocess"
    os.environ["BLENDER_PATH"] = BLENDER_PATH
    os.environ["BLENDER_TIMEOUT_SECONDS"] = "600"

    from blender_codex_mcp.server import blender_exec_python

    result = blender_exec_python(
        blender_source(),
        blend_file=str(BLEND_PATH),
        timeout_seconds=600,
    )
    gif_result = make_gif() if result.get("ok") else {"ok": False, "skipped": True}
    payload = {"blender_result": result, "gif_result": gif_result}
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:5000])
    return 0 if result.get("ok") and gif_result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
