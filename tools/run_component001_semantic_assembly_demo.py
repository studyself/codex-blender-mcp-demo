from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
ASSET_DIR = ROOT / "assets" / "nidorx_matcaps_scene"
MATCAP_DIR = ROOT / "assets" / "matcaps"
SOURCE_BLEND = ASSET_DIR / "scene.blend"
REFERENCE_IMAGE = ASSET_DIR / "repository-open-graph.jpg"
INFO_IMAGE = ASSET_DIR / "preview-info.png"
MATCAP_TEXTURES = [
    MATCAP_DIR / "1D3FCC_051B5F_81A0F2_5579E9-256px.png",
    MATCAP_DIR / "04E8E8_04B5B5_04CCCC_33FCFC-256px.png",
    MATCAP_DIR / "A27216_E9D036_D0AB24_DCB927-256px.png",
    MATCAP_DIR / "AC171C_FA8593_E84854_D3464E-256px.png",
    MATCAP_DIR / "80CA23_B7EE37_D5FA4C_A3E434-256px.png",
    MATCAP_DIR / "9F9F9F_E4E4E4_D4D4D4_CCCCCC-256px.png",
]

OUT_DIR = ROOT / "outputs" / "matcap_bust_component001_assembly"
FRAME_DIR = OUT_DIR / "animation_frames"
BLEND_PATH = OUT_DIR / "component001_semantic_assembly.blend"
HERO_PATH = OUT_DIR / "component001_semantic_assembly_hero.png"
GIF_PATH = OUT_DIR / "component001_semantic_assembly_animation.gif"
SUMMARY_PATH = OUT_DIR / "component001_semantic_assembly_summary.json"


PROMPT = """Create a Codex + Blender animation case based on nidorx/matcaps:
use the repository's female sci-fi bust, isolate component_001, split that
continuous mesh into semantic modules, animate those modules disassembling and
reassembling, and render a hero image plus an animation preview."""


def blender_source() -> str:
    source = dedent(
        """
        import json
        import math
        from pathlib import Path

        import bpy
        from mathutils import Vector

        out_dir = Path(__OUT_DIR__)
        frame_dir = Path(__FRAME_DIR__)
        blend_path = Path(__BLEND_PATH__)
        hero_path = Path(__HERO_PATH__)
        summary_path = Path(__SUMMARY_PATH__)
        reference_image = Path(__REFERENCE_IMAGE__)
        info_image = Path(__INFO_IMAGE__)
        matcap_textures = [Path(path) for path in __MATCAP_TEXTURES__]
        prompt = __PROMPT__

        out_dir.mkdir(parents=True, exist_ok=True)
        frame_dir.mkdir(parents=True, exist_ok=True)
        for old_frame in frame_dir.glob("frame_*.png"):
            old_frame.unlink()

        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = 90
        scene.frame_current = 1
        scene.render.fps = 18
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
        world.color = (0.008, 0.010, 0.016)

        def make_basic_mat(name, color, emission=False, strength=0.0, roughness=0.48):
            mat = bpy.data.materials.new(name)
            mat.diffuse_color = color
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                if "Base Color" in bsdf.inputs:
                    bsdf.inputs["Base Color"].default_value = color
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = roughness
                if "Metallic" in bsdf.inputs:
                    bsdf.inputs["Metallic"].default_value = 0.08
                if emission:
                    if "Emission Color" in bsdf.inputs:
                        bsdf.inputs["Emission Color"].default_value = color
                    if "Emission Strength" in bsdf.inputs:
                        bsdf.inputs["Emission Strength"].default_value = strength
            return mat

        def make_matcap_material(name, texture_path, tint=(1, 1, 1, 1), strength=0.92):
            image = bpy.data.images.load(str(texture_path))
            try:
                image.colorspace_settings.name = "sRGB"
            except Exception:
                pass
            mat = bpy.data.materials.new(name)
            mat.diffuse_color = tint
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()
            output = nodes.new("ShaderNodeOutputMaterial")
            emission = nodes.new("ShaderNodeEmission")
            tex = nodes.new("ShaderNodeTexImage")
            geom = nodes.new("ShaderNodeNewGeometry")
            scale = nodes.new("ShaderNodeVectorMath")
            add = nodes.new("ShaderNodeVectorMath")
            mix = nodes.new("ShaderNodeMix")

            tex.image = image
            tex.extension = "CLIP"
            tex.interpolation = "Cubic"
            scale.operation = "MULTIPLY"
            add.operation = "ADD"
            scale.inputs[1].default_value = (0.5, 0.5, 0.0)
            add.inputs[1].default_value = (0.5, 0.5, 0.0)
            try:
                mix.data_type = "RGBA"
                mix.factor_mode = "UNIFORM"
                mix.inputs["Factor"].default_value = 0.22
                mix.inputs["B"].default_value = tint
                links.new(tex.outputs["Color"], mix.inputs["A"])
                links.new(mix.outputs["Result"], emission.inputs["Color"])
            except Exception:
                links.new(tex.outputs["Color"], emission.inputs["Color"])

            links.new(geom.outputs["Normal"], scale.inputs[0])
            links.new(scale.outputs["Vector"], add.inputs[0])
            links.new(add.outputs["Vector"], tex.inputs["Vector"])
            emission.inputs["Strength"].default_value = strength
            links.new(emission.outputs["Emission"], output.inputs["Surface"])
            return mat

        m_white = make_basic_mat("codex_label_white", (0.92, 0.98, 1.0, 1), emission=True, strength=0.75)
        m_dim = make_basic_mat("codex_label_dim", (0.45, 0.62, 0.76, 1), emission=True, strength=0.28)
        m_cyan = make_basic_mat("codex_trace_cyan", (0.05, 0.75, 1.0, 1), emission=True, strength=1.0)
        m_orange = make_basic_mat("codex_phase_orange", (1.0, 0.42, 0.12, 1), emission=True, strength=1.45)
        m_floor = make_basic_mat("codex_floor_graphite", (0.024, 0.027, 0.034, 1))
        m_grid = make_basic_mat("codex_floor_grid", (0.04, 0.34, 0.72, 1), emission=True, strength=0.38)

        # Keep the actual bust source but remove unrelated preview meshes.
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

        loose_parts = [
            obj for obj in bpy.data.objects
            if obj.type == "MESH" and obj.name.startswith("PreviewSolideFemaleSCIFIbust")
        ]
        loose_parts.sort(key=lambda obj: len(obj.data.vertices), reverse=True)
        main = loose_parts[0]
        main.name = "component_001_source_continuous_mesh"

        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj != main:
                obj.hide_render = True
                obj.hide_viewport = True

        mesh = main.data
        mesh.update()
        local_vertices = [vertex.co.copy() for vertex in mesh.vertices]
        world_vertices = [main.matrix_world @ vertex for vertex in local_vertices]
        min_x = min(vertex.x for vertex in world_vertices); max_x = max(vertex.x for vertex in world_vertices)
        min_y = min(vertex.y for vertex in world_vertices); max_y = max(vertex.y for vertex in world_vertices)
        min_z = min(vertex.z for vertex in world_vertices); max_z = max(vertex.z for vertex in world_vertices)
        min_lx = min(vertex.x for vertex in local_vertices); max_lx = max(vertex.x for vertex in local_vertices)
        min_lz = min(vertex.z for vertex in local_vertices); max_lz = max(vertex.z for vertex in local_vertices)
        center = Vector(((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2))

        def clamp01(value):
            return max(0.0, min(1.0, value))

        def height_t(world_point):
            return clamp01((world_point.z - min_z) / max(max_z - min_z, 1e-6))

        def front_t(local_point):
            return clamp01((local_point.z - min_lz) / max(max_lz - min_lz, 1e-6))

        def side_t(local_point):
            return clamp01((local_point.x - min_lx) / max(max_lx - min_lx, 1e-6))

        regions = [
            {"name": "cranial_shell", "label": "cranial shell", "tint": (0.35, 0.82, 1.00, 1), "offset": (0.00, 0.18, 0.56), "rot": (0, -8, 2)},
            {"name": "face_mask", "label": "face mask", "tint": (0.93, 0.97, 1.00, 1), "offset": (0.72, 0.30, 0.12), "rot": (0, 10, -4)},
            {"name": "jaw_neck_front", "label": "jaw + front neck", "tint": (0.20, 0.98, 0.84, 1), "offset": (0.45, 0.24, -0.02), "rot": (-4, 10, 0)},
            {"name": "rear_head_plate", "label": "rear head plate", "tint": (0.56, 0.70, 1.00, 1), "offset": (-0.36, -0.46, 0.24), "rot": (2, -12, 8)},
            {"name": "temple_ear_module", "label": "temple / ear module", "tint": (1.00, 0.38, 0.78, 1), "offset": (-0.02, 0.60, 0.12), "rot": (8, 0, 10)},
            {"name": "neck_spine", "label": "neck spine", "tint": (1.00, 0.60, 0.22, 1), "offset": (-0.36, -0.52, -0.02), "rot": (10, -8, 0)},
            {"name": "upper_chest_shell", "label": "upper chest shell", "tint": (0.28, 0.84, 1.00, 1), "offset": (0.45, 0.28, -0.22), "rot": (-6, 8, -6)},
            {"name": "front_bust_pod", "label": "front bust pod", "tint": (1.00, 0.36, 0.30, 1), "offset": (0.75, 0.40, -0.42), "rot": (-10, 6, -8)},
            {"name": "side_rib_panel", "label": "side rib panel", "tint": (0.72, 1.00, 0.32, 1), "offset": (0.05, 0.64, -0.28), "rot": (4, 0, 12)},
            {"name": "rear_torso_shell", "label": "rear torso shell", "tint": (0.80, 0.54, 1.00, 1), "offset": (-0.55, -0.58, -0.32), "rot": (0, -14, 4)},
            {"name": "lower_base_block", "label": "lower base block", "tint": (0.95, 0.86, 0.64, 1), "offset": (-0.14, -0.08, -0.65), "rot": (-8, 0, 0)},
            {"name": "connector_transition", "label": "connector transition", "tint": (0.82, 0.88, 0.96, 1), "offset": (0.10, 0.02, -0.48), "rot": (8, 4, -4)},
        ]

        matcap_materials = []
        for idx, region in enumerate(regions):
            texture_path = matcap_textures[idx % len(matcap_textures)]
            matcap_materials.append(make_matcap_material("semantic_matcap_" + region["name"], texture_path, region["tint"]))

        def assign_region(local_center, world_center):
            h = height_t(world_center)
            f = front_t(local_center)
            s = side_t(local_center)

            if h > 0.73 and f > 0.64:
                return 1
            if h > 0.71:
                return 0
            if h > 0.58 and f < 0.42:
                return 3
            if h > 0.56 and 0.38 <= f <= 0.72 and (s < 0.34 or s > 0.66):
                return 4
            if h > 0.55 and f >= 0.58:
                return 1
            if 0.39 < h <= 0.62 and f >= 0.58:
                return 2
            if 0.34 < h <= 0.65 and f < 0.48:
                return 5
            if h <= 0.18:
                return 10 if f < 0.58 else 11
            if 0.18 < h <= 0.34 and f >= 0.63:
                return 7
            if 0.18 < h <= 0.44 and f < 0.47:
                return 9
            if 0.25 < h <= 0.52 and (s < 0.27 or s > 0.73):
                return 8
            if 0.31 < h <= 0.52 and f >= 0.50:
                return 6
            if f < 0.50:
                return 9
            return 6

        region_faces = [[] for _ in regions]
        face_counts = [0 for _ in regions]
        for poly in mesh.polygons:
            local_center = sum((mesh.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
            world_center = main.matrix_world @ local_center
            region_idx = assign_region(local_center, world_center)
            region_faces[region_idx].append(tuple(poly.vertices))
            face_counts[region_idx] += 1

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
            index_map = {old: new for new, old in enumerate(used)}
            verts_new = [local_vertices[old] for old in used]
            faces_new = [tuple(index_map[vertex_index] for vertex_index in face) for face in faces]
            mesh_new = bpy.data.meshes.new(f"component001_semantic_mesh_{idx:02d}_{region['name']}")
            mesh_new.from_pydata(verts_new, [], faces_new)
            mesh_new.update()
            for poly in mesh_new.polygons:
                poly.use_smooth = True
            obj_new = bpy.data.objects.new(f"component001_semantic_part_{idx:02d}_{region['name']}", mesh_new)
            obj_new.matrix_world = main.matrix_world.copy()
            bpy.context.collection.objects.link(obj_new)
            obj_new.data.materials.append(matcap_materials[idx - 1])
            obj_new["semantic_label"] = region["label"]
            region_objects.append(obj_new)

        def bounds_for(obj):
            coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            min_v = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
            max_v = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
            return min_v, max_v, (min_v + max_v) / 2

        def text_obj(name, body, loc, size, material=m_white, align="CENTER", rotation=(math.radians(68), 0, 0)):
            bpy.ops.object.text_add(location=loc, rotation=rotation)
            obj = bpy.context.object
            obj.name = name
            obj.data.body = body
            obj.data.align_x = align
            obj.data.align_y = "CENTER"
            obj.data.size = size
            obj.data.extrude = 0.004
            obj.data.bevel_depth = 0.0008
            obj.data.materials.append(material)
            return obj

        def cube(name, loc, scale, material, rotation=(0, 0, 0)):
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rotation)
            obj = bpy.context.object
            obj.name = name
            obj.scale = scale
            obj.data.materials.append(material)
            return obj

        def cylinder_between(name, start, end, radius, material):
            s = Vector(start)
            e = Vector(end)
            delta = e - s
            if delta.length <= 1e-6:
                return None
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=delta.length, location=(s + e) / 2)
            obj = bpy.context.object
            obj.name = name
            obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
            obj.data.materials.append(material)
            return obj

        def image_plane(name, image_path, loc, scale, rotation=(math.radians(72), 0, 0)):
            image = bpy.data.images.load(str(image_path))
            mat_img = bpy.data.materials.new(name + "_mat")
            mat_img.use_nodes = True
            nodes = mat_img.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            tex = nodes.new("ShaderNodeTexImage")
            tex.image = image
            if bsdf:
                mat_img.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                if "Emission Color" in bsdf.inputs:
                    mat_img.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = 0.22
            bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rotation)
            obj = bpy.context.object
            obj.name = name
            obj.scale = scale
            obj.data.materials.append(mat_img)
            return obj

        base_locations = [obj.location.copy() for obj in region_objects]
        base_rotations = [obj.rotation_euler.copy() for obj in region_objects]
        explode_locations = []
        explode_rotations = []
        for obj, base_location, base_rotation, region in zip(region_objects, base_locations, base_rotations, regions):
            offset = Vector(region["offset"])
            explode_locations.append(base_location + offset * 0.92)
            rot_delta = region["rot"]
            explode_rotations.append((
                base_rotation.x + math.radians(rot_delta[0]),
                base_rotation.y + math.radians(rot_delta[1]),
                base_rotation.z + math.radians(rot_delta[2]),
            ))

        # Keyframe the semantic parts: assembled, detach, exploded hold, reassembly.
        for obj, base_location, base_rotation, explode_location, explode_rotation in zip(
            region_objects, base_locations, base_rotations, explode_locations, explode_rotations
        ):
            for frame, location, rotation in [
                (1, base_location, base_rotation),
                (18, base_location, base_rotation),
                (46, explode_location, explode_rotation),
                (62, explode_location, explode_rotation),
                (90, base_location, base_rotation),
            ]:
                scene.frame_set(frame)
                obj.location = location
                obj.rotation_euler = rotation
                obj.keyframe_insert(data_path="location", frame=frame)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)

        # Clean final render: only the sculpture modules are visible.
        # No text overlays, reference cards, floor grid, guide axes, UI bars, or rectangles.
        for obj in bpy.data.objects:
            if obj.type in {"FONT", "CURVE"}:
                obj.hide_render = True
                obj.hide_viewport = True

        # Lights.
        bpy.ops.object.light_add(type="AREA", location=(center.x + 0.45, center.y - 3.6, center.z + 3.2))
        key = bpy.context.object
        key.name = "component001_key_softbox"
        key.data.energy = 520
        key.data.size = 4.8
        bpy.ops.object.light_add(type="POINT", location=(center.x - 2.4, center.y + 1.4, center.z + 1.9))
        rim = bpy.context.object
        rim.name = "component001_blue_rim"
        rim.data.energy = 220
        rim.data.color = (0.18, 0.68, 1.0)
        bpy.ops.object.light_add(type="POINT", location=(center.x + 1.9, center.y - 0.65, center.z + 0.35))
        warm = bpy.context.object
        warm.name = "component001_warm_scan_light"
        warm.data.energy = 90
        warm.data.color = (1.0, 0.42, 0.18)

        cam = bpy.data.objects.get("Camera")
        if cam is None:
            bpy.ops.object.camera_add()
            cam = bpy.context.object
        cam.name = "camera_component001_assembly"
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 3.05
        scene.camera = cam

        def aim_camera(location, target):
            cam.location = Vector(location)
            direction = Vector(target) - cam.location
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

        target = (center.x, center.y, center.z + 0.05)
        camera_keys = [
            (1, (center.x + 2.85, center.y - 3.55, center.z + 1.48), 3.05),
            (46, (center.x + 2.55, center.y - 3.80, center.z + 1.66), 3.35),
            (90, (center.x + 2.85, center.y - 3.55, center.z + 1.48), 3.05),
        ]
        for frame, loc, ortho in camera_keys:
            scene.frame_set(frame)
            aim_camera(loc, target)
            cam.data.ortho_scale = ortho
            cam.keyframe_insert(data_path="location", frame=frame)
            cam.keyframe_insert(data_path="rotation_euler", frame=frame)
            cam.data.keyframe_insert(data_path="ortho_scale", frame=frame)

        try:
            bpy.ops.file.pack_all()
        except Exception:
            pass

        scene.frame_set(46)
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        scene.render.filepath = str(hero_path)
        bpy.ops.render.render(write_still=True)

        scene.render.resolution_x = 800
        scene.render.resolution_y = 450
        scene.render.filepath = str(frame_dir / "frame_")
        bpy.ops.render.render(animation=True)

        summary = {
            "name": "COMPONENT_001 SEMANTIC ASSEMBLY",
            "source_project": "https://github.com/nidorx/matcaps",
            "source_object": "PreviewSolideFemaleSCIFIbust",
            "source_component": "component_001, largest continuous loose mesh",
            "method": "semantic segmentation of a continuous mesh, then keyframed disassembly and reassembly",
            "prompt": prompt,
            "semantic_part_count": len(region_objects),
            "regions": [
                {
                    "index": idx,
                    "name": region["name"],
                    "label": region["label"],
                    "face_count": face_counts[idx - 1],
                }
                for idx, region in enumerate(regions, start=1)
            ],
            "blend_path": str(blend_path),
            "hero_path": str(hero_path),
            "frame_dir": str(frame_dir),
            "animation_gif": __GIF_PATH_TEXT__,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "fps": scene.render.fps,
            "hero_resolution": [1920, 1080],
            "animation_resolution": [800, 450],
            "engine": scene.render.engine,
        }
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print("__COMPONENT001_ASSEMBLY_START__")
        print(json.dumps(summary, ensure_ascii=False))
        print("__COMPONENT001_ASSEMBLY_END__")
        """
    )
    replacements = {
        "__OUT_DIR__": repr(str(OUT_DIR)),
        "__FRAME_DIR__": repr(str(FRAME_DIR)),
        "__BLEND_PATH__": repr(str(BLEND_PATH)),
        "__HERO_PATH__": repr(str(HERO_PATH)),
        "__SUMMARY_PATH__": repr(str(SUMMARY_PATH)),
        "__REFERENCE_IMAGE__": repr(str(REFERENCE_IMAGE)),
        "__INFO_IMAGE__": repr(str(INFO_IMAGE)),
        "__MATCAP_TEXTURES__": repr([str(path) for path in MATCAP_TEXTURES]),
        "__PROMPT__": repr(PROMPT),
        "__GIF_PATH_TEXT__": repr(str(GIF_PATH)),
    }
    for key, value in replacements.items():
        source = source.replace(key, value)
    return source


def run_blender(blender_path: str) -> subprocess.CompletedProcess[str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = OUT_DIR / "_run_component001_semantic_assembly_in_blender.py"
    script_path.write_text(blender_source(), encoding="utf-8")
    command = [
        blender_path,
        "--background",
        str(SOURCE_BLEND),
        "--python",
        str(script_path),
    ]
    return subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=1200,
    )


def make_gif() -> dict:
    frames = sorted(FRAME_DIR.glob("frame_*.png"))
    if not frames:
        return {"ok": False, "error": "No rendered PNG frames found.", "frame_dir": str(FRAME_DIR)}

    images = []
    for path in frames:
        with Image.open(path) as image:
            images.append(image.convert("P", palette=Image.Palette.ADAPTIVE, colors=160).copy())

    first, rest = images[0], images[1:]
    first.save(
        GIF_PATH,
        save_all=True,
        append_images=rest,
        duration=56,
        loop=0,
        optimize=True,
    )

    with Image.open(GIF_PATH) as gif:
        return {
            "ok": True,
            "gif_path": str(GIF_PATH),
            "frame_count": sum(1 for _ in ImageSequence.Iterator(gif)),
            "size": gif.size,
        }


def update_summary(gif_result: dict, blender_result: subprocess.CompletedProcess[str]) -> dict:
    if SUMMARY_PATH.exists():
        payload = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    else:
        payload = {}
    payload["gif"] = gif_result
    payload["blender_return_code"] = blender_result.returncode
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", default=DEFAULT_BLENDER)
    args = parser.parse_args()

    missing = [
        path
        for path in [SOURCE_BLEND, REFERENCE_IMAGE, INFO_IMAGE, *MATCAP_TEXTURES]
        if not path.exists()
    ]
    if missing:
        print("Missing required assets:")
        print("\n".join(str(path) for path in missing))
        return 1

    result = run_blender(args.blender)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        return result.returncode

    gif_result = make_gif()
    payload = update_summary(gif_result, result)
    print(json.dumps({"ok": gif_result.get("ok", False), "summary": payload}, indent=2, ensure_ascii=False))
    return 0 if gif_result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
