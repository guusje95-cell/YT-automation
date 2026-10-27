"""Blender (bpy) test scene: a car on a desert highway at sunset, camera tracking low beside it.

Run with the Blender venv:  /root/venv-blender/bin/python blender_car.py MODEL.glb OUT_DIR [frames] [samples] [res%]
Writes OUT_DIR/frame_####.png. Cycles on CPU with OpenImageDenoise.
"""
import math
import sys

import bpy

model, out_dir = sys.argv[1], sys.argv[2]
frames = int(sys.argv[3]) if len(sys.argv) > 3 else 1
samples = int(sys.argv[4]) if len(sys.argv) > 4 else 32
res_pct = int(sys.argv[5]) if len(sys.argv) > 5 else 100

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = samples
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = res_pct
sc.render.fps = 30
sc.frame_start, sc.frame_end = 1, frames
sc.render.use_motion_blur = True
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"

# --- sky: physical sun low on the horizon
world = bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
nt = world.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = "MULTIPLE_SCATTERING" if "MULTIPLE_SCATTERING" in [i.identifier for i in sky.bl_rna.properties["sky_type"].enum_items] else sky.sky_type
sky.sun_elevation = math.radians(3.0)
sky.sun_rotation = math.radians(200)
bg = nt.nodes["Background"]
bg.inputs["Strength"].default_value = 0.35
nt.links.new(sky.outputs["Color"], bg.inputs["Color"])

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.data.color = (1.0, 0.62, 0.38)
sun.data.angle = math.radians(1.5)
sun.rotation_euler = (math.radians(87), 0, math.radians(200 - 180))
sc.collection.objects.link(sun)

# --- road and desert
def mat(name, color, rough=0.8, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if coat:
        p.inputs["Coat Weight"].default_value = coat
    return m

bpy.ops.mesh.primitive_plane_add(size=1)
ground = bpy.context.object
ground.scale = (4000, 4000, 1)
ground.data.materials.append(mat("desert", (0.32, 0.20, 0.12), 0.95))
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.005))
road = bpy.context.object
road.scale = (9, 4000, 1)
road.data.materials.append(mat("asphalt", (0.035, 0.035, 0.04), 0.55))
line_m = mat("line", (0.9, 0.7, 0.15), 0.4)
for k in range(-200, 200):          # dashed centre line
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, k * 12.0, 0.01))
    d = bpy.context.object
    d.scale = (0.15, 4.0, 1)
    d.data.materials.append(line_m)

# --- the car
bpy.ops.import_scene.gltf(filepath=model)
car_parts = [o for o in bpy.context.selected_objects]
root = bpy.data.objects.new("car_root", None)
sc.collection.objects.link(root)
for o in car_parts:
    if o.parent is None:
        o.parent = root
paint = mat("paint", (0.55, 0.02, 0.02), 0.22, 0.6, 1.0)
for o in car_parts:
    if o.type == "MESH":
        for i, slot in enumerate(o.material_slots):
            n = (slot.material.name if slot.material else "").lower()
            if not any(k in n for k in ("window", "glass", "tire", "wheel", "black", "light")):
                o.material_slots[i].material = paint
root.scale = (2.2, 2.2, 2.2)
root.rotation_euler = (0, 0, math.radians(180))
speed = 3.0                                  # metres per frame (= 90 m/s at 30 fps)
for f in (1, max(frames, 2)):
    root.location = (2.2, -(f - 1) * speed, 0)
    root.keyframe_insert("location", frame=f)
for fc in (root.animation_data.action.fcurves if hasattr(root.animation_data.action, "fcurves") else []):
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"

# --- camera: low, beside and slightly ahead, tracking the car
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 35
cam.data.dof.use_dof = True
cam.data.dof.focus_object = root
cam.data.dof.aperture_fstop = 2.8
sc.collection.objects.link(cam)
sc.camera = cam
cam.parent = root
cam.location = (3.2, -2.4, 0.45)
tc = cam.constraints.new("TRACK_TO")
tc.target = root
tc.track_axis, tc.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"

sc.render.filepath = f"{out_dir}/frame_"
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(animation=True)
