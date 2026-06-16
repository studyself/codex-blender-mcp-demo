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
OUT_DIR = ROOT / "outputs" / "codex_blender_case"
BLEND_PATH = OUT_DIR / "codex_blender_mcp_case.blend"
RENDER_PATH = OUT_DIR / "codex_blender_mcp_case.png"
SUMMARY_PATH = OUT_DIR / "codex_blender_mcp_case_summary.json"


def blender_source() -> str:
    source = dedent(
        """
        import json
        import math
        from pathlib import Path

        import bpy
        from mathutils import Vector

        out_dir = Path(__OUT_DIR__)
        blend_path = Path(__BLEND_PATH__)
        render_path = Path(__RENDER_PATH__)
        out_dir.mkdir(parents=True, exist_ok=True)

        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = 120
        scene.frame_current = 60
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.film_transparent = False
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
        world.color = (0.018, 0.022, 0.032)

        def mat(name, color, emission=False, strength=0.0, roughness=0.45):
            material = bpy.data.materials.new(name)
            material.use_nodes = True
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                try:
                    bsdf.inputs["Base Color"].default_value = color
                except Exception:
                    pass
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = roughness
                if emission:
                    if "Emission Color" in bsdf.inputs:
                        bsdf.inputs["Emission Color"].default_value = color
                    if "Emission Strength" in bsdf.inputs:
                        bsdf.inputs["Emission Strength"].default_value = strength
            return material

        m_floor = mat("mat_floor_graphite", (0.035, 0.042, 0.055, 1))
        m_grid = mat("mat_grid_cyan", (0.05, 0.42, 0.75, 1), emission=True, strength=0.35)
        m_panel = mat("mat_panel_blue_black", (0.04, 0.065, 0.09, 1), roughness=0.25)
        m_panel_edge = mat("mat_panel_edge", (0.03, 0.85, 0.95, 1), emission=True, strength=1.3)
        m_text = mat("mat_text_white", (0.92, 0.98, 1.0, 1), emission=True, strength=0.7)
        m_text_dim = mat("mat_text_dim", (0.48, 0.7, 0.82, 1), emission=True, strength=0.3)
        m_code = mat("mat_code_green", (0.22, 1.0, 0.55, 1), emission=True, strength=0.9)
        m_orange = mat("mat_codex_orange", (1.0, 0.42, 0.18, 1), emission=True, strength=1.2)
        m_asset = mat("mat_asset_titanium", (0.62, 0.68, 0.72, 1), roughness=0.32)
        m_asset_dark = mat("mat_asset_dark", (0.08, 0.09, 0.1, 1), roughness=0.55)
        m_glass = mat("mat_translucent_blue", (0.1, 0.55, 1.0, 0.38), emission=True, strength=0.18)
        m_node = mat("mat_node_boxes", (0.08, 0.18, 0.19, 1), roughness=0.25)

        def cube(name, loc, scale, material):
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
            obj = bpy.context.object
            obj.name = name
            obj.scale = scale
            if material:
                obj.data.materials.append(material)
            return obj

        def cyl(name, loc, radius, depth, material, rotation=(0, 0, 0), vertices=48):
            bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
            obj = bpy.context.object
            obj.name = name
            if material:
                obj.data.materials.append(material)
            return obj

        def cone(name, loc, radius1, depth, material, direction):
            bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=radius1, radius2=0, depth=depth, location=loc)
            obj = bpy.context.object
            obj.name = name
            obj.rotation_euler = Vector(direction).to_track_quat("Z", "Y").to_euler()
            if material:
                obj.data.materials.append(material)
            return obj

        def cylinder_between(name, start, end, radius, material, vertices=24):
            s = Vector(start)
            e = Vector(end)
            mid = (s + e) / 2
            delta = e - s
            length = delta.length
            if length == 0:
                return None
            obj = cyl(name, mid, radius, length, material, vertices=vertices)
            obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
            return obj

        def text_obj(name, body, loc, size, material=m_text, align="CENTER", rotation=(math.radians(90), 0, 0)):
            bpy.ops.object.text_add(location=loc, rotation=rotation)
            obj = bpy.context.object
            obj.name = name
            obj.data.body = body
            obj.data.align_x = align
            obj.data.align_y = "CENTER"
            obj.data.size = size
            obj.data.extrude = 0.01
            obj.data.bevel_depth = 0.0012
            obj.data.resolution_u = 12
            if material:
                obj.data.materials.append(material)
            return obj

        def curve(name, points, material, bevel=0.025):
            data = bpy.data.curves.new(name, "CURVE")
            data.dimensions = "3D"
            data.resolution_u = 2
            data.bevel_depth = bevel
            data.bevel_resolution = 5
            spline = data.splines.new("POLY")
            spline.points.add(len(points) - 1)
            for p, co in zip(spline.points, points):
                p.co = (co[0], co[1], co[2], 1)
            obj = bpy.data.objects.new(name, data)
            bpy.context.collection.objects.link(obj)
            if material:
                data.materials.append(material)
            return obj

        # Floor and grid.
        cube("stage_floor", (0, 0.25, -0.04), (9.4, 5.2, 0.08), m_floor)
        for x in [i * 0.5 for i in range(-9, 10)]:
            cube(f"grid_x_{x:.1f}", (x, 0.25, 0.006), (0.012, 4.6, 0.012), m_grid)
        for y in [i * 0.5 for i in range(-4, 6)]:
            cube(f"grid_y_{y:.1f}", (0, y, 0.008), (8.8, 0.012, 0.012), m_grid)

        # Title.
        text_obj("title_codex_blender", "CODEX -> BLENDER", (0, -0.62, 3.55), 0.48, m_text)
        text_obj("subtitle_mcp", "MCP subprocess control | Blender 5.1.2 | generated .blend + render", (0, -0.62, 3.13), 0.13, m_text_dim)

        # Prompt panel.
        cube("prompt_panel", (-3.25, 0.05, 1.65), (2.55, 0.08, 2.05), m_panel)
        cube("prompt_panel_top_edge", (-3.25, -0.01, 2.72), (2.62, 0.04, 0.04), m_panel_edge)
        text_obj("prompt_header", "PROMPT", (-3.25, -0.08, 2.48), 0.24, m_orange)
        prompt_lines = [
            "Create a compact sci-fi rover",
            "show the Codex -> MCP -> Blender loop",
            "add materials, lights, labels",
            "save the scene and render a proof image",
        ]
        for i, line in enumerate(prompt_lines):
            text_obj(f"prompt_line_{i}", line, (-3.25, -0.08, 2.1 - i * 0.28), 0.105, m_text_dim)
        text_obj("prompt_footer", "one instruction becomes editable 3D content", (-3.25, -0.08, 0.78), 0.095, m_code)

        # MCP bridge tower.
        cyl("mcp_core", (0, 0.1, 1.45), 0.38, 1.8, m_glass, vertices=64)
        for z in [0.62, 1.05, 1.48, 1.91, 2.34]:
            cyl(f"mcp_ring_{z:.2f}", (0, 0.1, z), 0.47, 0.04, m_panel_edge, vertices=72)
        text_obj("mcp_label", "MCP", (0, -0.52, 1.58), 0.31, m_text)
        text_obj("mcp_tool_1", "blender_exec_python()", (-0.95, -0.12, 2.48), 0.09, m_code, align="LEFT")
        text_obj("mcp_tool_2", "blender_scene_info()", (-0.95, -0.12, 2.25), 0.09, m_code, align="LEFT")
        text_obj("mcp_tool_3", "save_as_mainfile()", (-0.95, -0.12, 2.02), 0.09, m_code, align="LEFT")

        # Flow arrows.
        cylinder_between("arrow_prompt_to_mcp", (-1.9, 0.05, 1.55), (-0.55, 0.05, 1.55), 0.045, m_orange)
        cone("arrow_prompt_to_mcp_head", (-0.43, 0.05, 1.55), 0.12, 0.24, m_orange, (1, 0, 0))
        cylinder_between("arrow_mcp_to_asset", (0.55, 0.05, 1.55), (1.95, 0.05, 1.55), 0.045, m_panel_edge)
        cone("arrow_mcp_to_asset_head", (2.08, 0.05, 1.55), 0.12, 0.24, m_panel_edge, (1, 0, 0))
        curve("signal_arc_high", [(-2.0, -0.15, 2.55), (-0.8, -0.45, 3.0), (0.2, -0.28, 2.42), (1.55, -0.25, 2.78), (2.8, -0.18, 2.55)], m_code, 0.018)
        curve("signal_arc_low", [(-2.0, -0.18, 0.78), (-0.9, -0.42, 0.52), (0.3, -0.3, 0.86), (1.45, -0.22, 0.62), (2.75, -0.2, 0.82)], m_panel_edge, 0.014)

        # Node boxes.
        node_data = [
            ("mesh", 1.35),
            ("nodes", 1.68),
            ("materials", 2.01),
            ("render", 2.34),
        ]
        for idx, (label, z) in enumerate(node_data):
            cube(f"node_{label}", (1.05, 0.1, z), (0.86, 0.08, 0.22), m_node)
            text_obj(f"node_label_{label}", label, (1.05, -0.02, z), 0.09, m_code)
            if idx > 0:
                cylinder_between(f"node_link_{idx}", (1.05, 0.06, node_data[idx - 1][1] + 0.13), (1.05, 0.06, z - 0.13), 0.015, m_code)

        # Generated rover asset.
        cube("rover_chassis", (3.0, 0.25, 0.68), (1.32, 0.82, 0.28), m_asset)
        cube("rover_top_deck", (3.0, 0.25, 0.95), (0.86, 0.56, 0.17), m_asset)
        cube("rover_front_sensor", (3.0, -0.24, 1.08), (0.42, 0.08, 0.16), m_glass)
        for ix, x in enumerate([2.35, 3.65]):
            for y in [-0.14, 0.66]:
                wheel = cyl(f"wheel_{ix}_{y}", (x, y, 0.4), 0.25, 0.18, m_asset_dark, rotation=(math.radians(90), 0, 0), vertices=48)
                cyl(f"wheel_hub_{ix}_{y}", (x, y, 0.4), 0.095, 0.2, m_panel_edge, rotation=(math.radians(90), 0, 0), vertices=32)
        cylinder_between("rover_arm_1", (3.15, 0.25, 1.05), (3.55, 0.18, 1.55), 0.06, m_asset)
        cylinder_between("rover_arm_2", (3.55, 0.18, 1.55), (3.9, 0.1, 1.28), 0.052, m_asset)
        cyl("rover_joint_1", (3.15, 0.25, 1.05), 0.12, 0.14, m_orange, rotation=(math.radians(90), 0, 0), vertices=32)
        cyl("rover_joint_2", (3.55, 0.18, 1.55), 0.1, 0.13, m_orange, rotation=(math.radians(90), 0, 0), vertices=32)
        cube("rover_gripper", (4.02, 0.08, 1.23), (0.12, 0.22, 0.05), m_orange)
        text_obj("asset_label", "GENERATED ASSET", (3.0, -0.46, 1.82), 0.18, m_text)
        text_obj("asset_caption", ".blend saved | PNG rendered | scene inspected", (3.0, -0.46, 1.57), 0.09, m_text_dim)

        # Floating proof markers.
        for i, label in enumerate(["01 prompt", "02 code", "03 geometry", "04 render"]):
            x = -4.2 + i * 2.75
            cube(f"proof_badge_{i}", (x, -0.25, 0.25), (0.72, 0.06, 0.18), m_panel)
            text_obj(f"proof_label_{i}", label, (x, -0.32, 0.25), 0.073, m_text_dim)

        # Lighting.
        bpy.ops.object.light_add(type="AREA", location=(-3.7, -4.2, 4.8))
        key = bpy.context.object
        key.name = "key_softbox"
        key.data.energy = 520
        key.data.size = 4.0
        bpy.ops.object.light_add(type="POINT", location=(2.8, -1.9, 2.7))
        rim = bpy.context.object
        rim.name = "cyan_rim_light"
        rim.data.energy = 250
        rim.data.color = (0.1, 0.8, 1.0)
        bpy.ops.object.light_add(type="POINT", location=(-1.0, -1.0, 1.8))
        warm = bpy.context.object
        warm.name = "orange_bridge_light"
        warm.data.energy = 150
        warm.data.color = (1.0, 0.44, 0.2)

        # Camera.
        bpy.ops.object.camera_add(location=(5.9, -6.9, 3.85))
        cam = bpy.context.object
        cam.name = "camera_article_hero"
        target = Vector((0.08, 0.12, 1.55))
        direction = target - Vector(cam.location)
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 34
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = direction.length
        cam.data.dof.aperture_fstop = 7.5
        scene.camera = cam

        # Add a small animation keyframe trail so the .blend is not just a still.
        mcp_core = bpy.data.objects["mcp_core"]
        mcp_core.rotation_euler.z = 0
        mcp_core.keyframe_insert(data_path="rotation_euler", frame=1)
        mcp_core.rotation_euler.z = math.radians(360)
        mcp_core.keyframe_insert(data_path="rotation_euler", frame=120)

        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        scene.render.filepath = str(render_path)
        bpy.ops.render.render(write_still=True)

        summary = {
            "blend_path": str(blend_path),
            "render_path": str(render_path),
            "object_count": len(bpy.data.objects),
            "materials": len(bpy.data.materials),
            "frame_range": [scene.frame_start, scene.frame_end],
            "engine": scene.render.engine,
            "camera": cam.name,
        }
        print("__CODEX_BLENDER_CASE_START__")
        print(json.dumps(summary, ensure_ascii=False))
        print("__CODEX_BLENDER_CASE_END__")
        """
    )
    return (
        source.replace("__OUT_DIR__", repr(str(OUT_DIR)))
        .replace("__BLEND_PATH__", repr(str(BLEND_PATH)))
        .replace("__RENDER_PATH__", repr(str(RENDER_PATH)))
    )


def main() -> int:
    os.environ["BLENDER_MCP_MODE"] = "subprocess"
    os.environ["BLENDER_PATH"] = BLENDER_PATH
    os.environ["BLENDER_TIMEOUT_SECONDS"] = "300"

    from blender_codex_mcp.server import blender_exec_python, blender_scene_info

    result = blender_exec_python(blender_source(), timeout_seconds=300)
    if not result.get("ok"):
        print(json.dumps(result, indent=2))
        return 1

    scene_info = blender_scene_info(blend_file=str(BLEND_PATH))
    payload = {
        "mcp_exec": result,
        "scene_info": scene_info,
        "outputs": {
            "blend": str(BLEND_PATH),
            "render": str(RENDER_PATH),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["outputs"], indent=2, ensure_ascii=False))
    if scene_info.get("ok"):
        print(json.dumps(scene_info.get("scene", {}), indent=2, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
