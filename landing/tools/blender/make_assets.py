"""Generate DealerWatch landing-page 3D assets with Blender (headless).

Run from the repository root:
    blender -b -P landing/tools/blender/make_assets.py -- landing/public/models

Produces:
    chain_link.glb  - one stadium-shaped chain link (instanced nine times in the page)
    slab.glb        - a bevelled order slab used for the sandwich scene
    seal.glb        - a bevelled disc used for the human-decision seal
"""
import math
import sys
from pathlib import Path

import bpy

argv = sys.argv
out_dir = Path(argv[argv.index("--") + 1] if "--" in argv else "landing/public/models")
out_dir.mkdir(parents=True, exist_ok=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def smooth(obj, angle_deg=40):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))
    except Exception:  # older/newer API differences
        bpy.ops.object.shade_smooth()


def export(obj, name):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(out_dir / f"{name}.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="NONE",
        export_normals=True,
        export_texcoords=False,
        export_animations=False,
    )


def stadium_points(length=1.0, radius=0.45, segments=48):
    """Closed stadium (two semicircles joined by straights) in the XY plane."""
    pts = []
    half = length / 2
    for i in range(segments // 2 + 1):
        a = -math.pi / 2 + math.pi * i / (segments // 2)
        pts.append((half + radius * math.cos(a), radius * math.sin(a), 0.0))
    for i in range(segments // 2 + 1):
        a = math.pi / 2 + math.pi * i / (segments // 2)
        pts.append((-half + radius * math.cos(a), radius * math.sin(a), 0.0))
    return pts


def make_chain_link():
    reset_scene()
    curve = bpy.data.curves.new("link", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = 0.14
    curve.bevel_resolution = 10
    curve.use_fill_caps = False
    spline = curve.splines.new("POLY")
    pts = stadium_points()
    spline.points.add(len(pts) - 1)
    for p, (x, y, z) in zip(spline.points, pts):
        p.co = (x, y, z, 1.0)
    spline.use_cyclic_u = True
    obj = bpy.data.objects.new("ChainLink", curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    smooth(obj)
    export(obj, "chain_link")


def make_slab():
    reset_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = "Slab"
    obj.scale = (1.6, 0.09, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 8
    bevel.limit_method = "ANGLE"
    smooth(obj, 35)
    export(obj, "slab")


def make_seal():
    reset_scene()
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.0, depth=0.16)
    obj = bpy.context.active_object
    obj.name = "Seal"
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.045
    bevel.segments = 10
    bevel.limit_method = "ANGLE"
    # inner ring groove for a stamp-like silhouette
    bpy.ops.mesh.primitive_torus_add(major_radius=0.78, minor_radius=0.03, major_segments=96, minor_segments=12)
    ring = bpy.context.active_object
    ring.location = (0, 0, 0.08)
    bool_mod = obj.modifiers.new("Groove", "BOOLEAN")
    bool_mod.operation = "DIFFERENCE"
    bool_mod.object = ring
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(ring, do_unlink=True)
    smooth(obj, 35)
    export(obj, "seal")


make_chain_link()
make_slab()
make_seal()
print("assets written to", out_dir)
