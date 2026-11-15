import sys

sys.path.insert(0, "/workspace/github__MSC-Git-debug__HR352_Boat_Inventory/blender_addon")

import bmesh
import bpy

import hull_watertight

hull_watertight.register()
props = bpy.context.scene.hull_wt

failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print("[{}] {} {}".format(status, name, detail))
    if not cond:
        failures.append(name)


def new_mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def cube_bm():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    return bm


def analyze():
    res = bpy.ops.mesh.hullwt_analyze()
    assert res == {'FINISHED'}
    return (props.stat_holes, props.stat_hole_edges, props.is_watertight,
            props.stat_nonmanifold, props.stat_parts)


# --- Test 1: cube missing one face -> 1 hole, fill closes it ---
obj = new_mesh_obj("CubeHole", cube_bm())
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[5]], context="FACES")
bm.to_mesh(obj.data)
bm.free()

bpy.ops.object.mode_set(mode='EDIT')
holes, hole_edges, wt, nm, parts = analyze()
check("t1 analyze detects hole", holes == 1 and hole_edges == 4, "holes={} edges={}".format(holes, hole_edges))
check("t1 not watertight", not wt)

props.max_hole_sides = 0
res = bpy.ops.mesh.hullwt_fill_holes()
assert res == {'FINISHED'}
holes, hole_edges, wt, nm, parts = analyze()
check("t1 fill closes hole", holes == 0 and hole_edges == 0, "holes={} edges={}".format(holes, hole_edges))
check("t1 watertight after fill", wt)
check("t1 face count restored", props.stat_faces == 6, "faces={}".format(props.stat_faces))
bpy.ops.object.mode_set(mode='OBJECT')

# --- Test 2: max hole size protection (hole of 6 edges must NOT fill with limit 4) ---
obj = new_mesh_obj("CubeTwoFaces", cube_bm())
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.faces.ensure_lookup_table()
f0 = bm.faces[0]
f1 = next(f for f in f0.edges[0].link_faces if f is not f0)
bmesh.ops.delete(bm, geom=[f0, f1], context="FACES")
bm.to_mesh(obj.data)
bm.free()

bpy.ops.object.mode_set(mode='EDIT')
holes, hole_edges, wt, nm, parts = analyze()
check("t2 two-face hole detected", holes == 1 and hole_edges == 6, "holes={} edges={}".format(holes, hole_edges))

props.max_hole_sides = 4
bpy.ops.mesh.hullwt_fill_holes()
holes, hole_edges, wt, nm, parts = analyze()
check("t2 big hole protected", holes == 1 and hole_edges == 6, "holes={} edges={}".format(holes, hole_edges))

props.max_hole_sides = 0
bpy.ops.mesh.hullwt_fill_holes()
holes, hole_edges, wt, nm, parts = analyze()
check("t2 big hole fills when unlimited", holes == 0 and wt, "holes={} wt={}".format(holes, wt))
bpy.ops.object.mode_set(mode='OBJECT')

# --- Test 3: messy mesh (doubles + loose vert + hole) fixed by one-click pipeline ---
obj = new_mesh_obj("Messy", cube_bm())
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[5]], context="FACES")
bm.to_mesh(obj.data)
bm.free()
me = obj.data
bm = bmesh.new()
bm.from_mesh(me)
bm2 = bmesh.new()
bm2.from_mesh(me)
me.update()  # ensure base saved
dup = bpy.data.meshes.new("tmpdup")
bm2.to_mesh(dup)
bm.from_mesh(dup)  # append duplicate geometry
bm.verts.new((10.0, 10.0, 10.0))  # loose vert
bm.to_mesh(me)
bm.free()
bpy.data.meshes.remove(dup)

bpy.ops.object.mode_set(mode='EDIT')
holes, hole_edges, wt, nm, parts = analyze()
check("t3 messy detected", holes == 2 and parts == 3 and props.stat_verts == 17,
      "holes={} parts={} verts={}".format(holes, parts, props.stat_verts))

props.weld_threshold = 0.001
props.max_hole_sides = 0
res = bpy.ops.mesh.hullwt_watertight_fix()
assert res == {'FINISHED'}
holes, hole_edges, wt, nm, parts = analyze()
check("t3 pipeline watertight", wt and holes == 0 and parts == 1 and props.stat_verts == 8,
      "wt={} holes={} parts={} verts={}".format(wt, holes, parts, props.stat_verts))
bpy.ops.object.mode_set(mode='OBJECT')

# --- Test 4: select boundary / non-manifold helpers ---
obj = new_mesh_obj("SelTest", cube_bm())
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[5]], context="FACES")
bm.to_mesh(obj.data)
bm.free()
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.hullwt_select_boundary()
bm = bmesh.from_edit_mesh(obj.data)
sel = [e for e in bm.edges if e.select]
check("t4 select boundary edges", len(sel) == 4, "selected={}".format(len(sel)))
bpy.ops.mesh.hullwt_select_nonmanifold()
res = bpy.ops.mesh.hullwt_recalc_normals()
assert res == {'FINISHED'}
bpy.ops.object.mode_set(mode='OBJECT')

print()
if failures:
    print("FAILED: {}".format(failures))
    sys.exit(1)
print("ALL TESTS PASSED")
