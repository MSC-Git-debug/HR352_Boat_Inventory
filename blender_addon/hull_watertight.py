bl_info = {
    "name": "Hull Watertight Repair",
    "author": "MSC-Git-debug",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar (N) > Hull Fix",
    "description": "Analyze a hull mesh, close holes step by step and make it watertight",
    "category": "Mesh",
}

import bmesh
import bpy


BIG = 1_000_000
DEGENERATE_EPS = 1e-7


def _active_mesh_bmesh(context):
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return None, None
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    return bmesh.from_edit_mesh(me), me


def _boundary_loops(bm):
    visited = set()
    loops = []
    for e0 in bm.edges:
        if not e0.is_boundary or e0 in visited:
            continue
        visited.add(e0)
        loop = [e0]
        for v_end in e0.verts:
            cur_v = e0.other_vert(v_end)
            prev_e = e0
            while True:
                candidates = [e for e in cur_v.link_edges
                              if e.is_boundary and e is not prev_e and e not in visited]
                if len(candidates) != 1:
                    break
                e = candidates[0]
                visited.add(e)
                loop.append(e)
                cur_v = e.other_vert(cur_v)
                if cur_v is v_end:
                    break
        loops.append(loop)
    return loops


def _loose_parts(bm):
    seen = set()
    parts = 0
    for v in bm.verts:
        if v in seen:
            continue
        parts += 1
        stack = [v]
        seen.add(v)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                other = e.other_vert(cur)
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
    return parts


def _mesh_stats(bm):
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    nonmanifold_edges = [e for e in bm.edges if len(e.link_faces) > 2]
    wire_edges = [e for e in bm.edges if len(e.link_faces) == 0]
    loose_verts = [v for v in bm.verts if len(v.link_edges) == 0]
    interior_faces = [f for f in bm.faces
                      if all(len(l.edge.link_faces) > 1 for l in f.loops)]
    degenerate_edges = [e for e in bm.edges if e.calc_length() <= DEGENERATE_EPS]
    holes = _boundary_loops(bm)
    parts = _loose_parts(bm)
    watertight = (not boundary_edges and not nonmanifold_edges
                  and parts == 1 and len(bm.faces) > 0)
    return {
        "verts": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "holes": len(holes),
        "hole_edges": len(boundary_edges),
        "largest_hole": max((len(l) for l in holes), default=0),
        "nonmanifold_edges": len(nonmanifold_edges),
        "wire_edges": len(wire_edges),
        "loose_verts": len(loose_verts),
        "interior_faces": len(interior_faces),
        "degenerate_edges": len(degenerate_edges),
        "loose_parts": parts,
        "watertight": watertight,
    }


def _stats_report(stats):
    return ("Holes: {} ({} boundary edges) | Non-manifold edges: {} | "
            "Islands: {} | Watertight: {}").format(
        stats["holes"], stats["hole_edges"], stats["nonmanifold_edges"],
        stats["loose_parts"], "YES" if stats["watertight"] else "NO")


def _store_stats(context, stats):
    props = context.scene.hull_wt
    props.analyzed = True
    props.stat_verts = stats["verts"]
    props.stat_edges = stats["edges"]
    props.stat_faces = stats["faces"]
    props.stat_holes = stats["holes"]
    props.stat_hole_edges = stats["hole_edges"]
    props.stat_largest_hole = stats["largest_hole"]
    props.stat_nonmanifold = stats["nonmanifold_edges"]
    props.stat_wire = stats["wire_edges"]
    props.stat_loose_verts = stats["loose_verts"]
    props.stat_interior = stats["interior_faces"]
    props.stat_degenerate = stats["degenerate_edges"]
    props.stat_parts = stats["loose_parts"]
    props.is_watertight = stats["watertight"]


class MeshHullWtOperator(bpy.types.Operator):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'


class HULLWT_OT_analyze(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_analyze"
    bl_label = "Analyze Mesh"
    bl_description = "Count holes (boundary loops), non-manifold edges, islands and report watertight status"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        stats = _mesh_stats(bm)
        _store_stats(context, stats)
        self.report({'INFO'} if stats["watertight"] else {'WARNING'}, _stats_report(stats))
        return {'FINISHED'}


class HULLWT_OT_select_boundary(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_select_boundary"
    bl_label = "Select Hole Edges"
    bl_description = "Select all boundary edges so you can inspect the holes before filling them"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(me)
        count = 0
        for e in bm.edges:
            if e.is_boundary:
                e.select = True
                count += 1
        bm.select_flush_mode()
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Selected {} boundary edges".format(count))
        return {'FINISHED'}


class HULLWT_OT_remove_doubles(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_remove_doubles"
    bl_label = "Merge by Distance"
    bl_description = "Weld overlapping vertices (first step: usually removes many false holes)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        props = context.scene.hull_wt
        before = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=props.weld_threshold)
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Merged {} vertices".format(before - len(bm.verts)))
        return {'FINISHED'}


class HULLWT_OT_delete_loose(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_delete_loose"
    bl_label = "Delete Loose"
    bl_description = "Delete loose vertices and edges that are not part of any face"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        geom = ([v for v in bm.verts if len(v.link_edges) == 0]
                + [e for e in bm.edges if len(e.link_faces) == 0])
        count = len(geom)
        if geom:
            bmesh.ops.delete(bm, geom=geom, context='VERTS')
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Deleted {} loose elements".format(count))
        return {'FINISHED'}


class HULLWT_OT_delete_interior(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_delete_interior"
    bl_label = "Delete Interior Faces"
    bl_description = "Delete faces whose edges are all shared by two faces (hidden inner walls)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        faces = [f for f in bm.faces
                 if all(len(l.edge.link_faces) > 1 for l in f.loops)]
        count = len(faces)
        if faces:
            bmesh.ops.delete(bm, geom=faces, context='FACES')
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Deleted {} interior faces".format(count))
        return {'FINISHED'}


class HULLWT_OT_dissolve_degenerate(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_dissolve_degenerate"
    bl_label = "Dissolve Degenerate"
    bl_description = "Dissolve zero-length edges and collapsed faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        props = context.scene.hull_wt
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=props.weld_threshold)
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Dissolved degenerate geometry")
        return {'FINISHED'}


class HULLWT_OT_fill_holes(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_fill_holes"
    bl_label = "Fill Holes"
    bl_description = "Fill boundary loops up to the max hole size (protects big openings while closing small holes)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        props = context.scene.hull_wt
        edges = [e for e in bm.edges if e.is_boundary]
        if props.fill_selected_only:
            edges = [e for e in edges if e.select]
        before_loops = len(_boundary_loops(bm))
        sides = props.max_hole_sides if props.max_hole_sides > 0 else BIG
        if not edges:
            self.report({'INFO'}, "No boundary edges to fill")
            return {'FINISHED'}
        result = bmesh.ops.holes_fill(bm, edges=edges, sides=sides)
        new_faces = result["faces"]
        if props.triangulate_fill and new_faces:
            bmesh.ops.triangulate(bm, faces=new_faces)
        bmesh.update_edit_mesh(me)
        after = _mesh_stats(bm)
        self.report({'INFO'}, "Added {} faces | Holes: {} -> {}".format(
            len(new_faces), before_loops, after["holes"]))
        return {'FINISHED'}


class HULLWT_OT_recalc_normals(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_recalc_normals"
    bl_label = "Recalc Normals Outside"
    bl_description = "Make all face normals consistent and pointing outside"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Normals recalculated outside")
        return {'FINISHED'}


class HULLWT_OT_select_nonmanifold(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_select_nonmanifold"
    bl_label = "Select Non-Manifold"
    bl_description = "Select edges shared by more than two faces or with no face at all"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        bpy.ops.mesh.select_mode(type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(me)
        count = 0
        for e in bm.edges:
            if len(e.link_faces) > 2 or len(e.link_faces) == 0:
                e.select = True
                count += 1
        bm.select_flush_mode()
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, "Selected {} non-manifold edges".format(count))
        return {'FINISHED'}


class HULLWT_OT_watertight_fix(MeshHullWtOperator):
    bl_idname = "mesh.hullwt_watertight_fix"
    bl_label = "Full Watertight Fix"
    bl_description = ("Run the full pipeline: merge, delete loose, delete interior, "
                      "dissolve degenerate, fill holes, recalc normals")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bm, me = _active_mesh_bmesh(context)
        if bm is None:
            return {'CANCELLED'}
        props = context.scene.hull_wt
        before = _mesh_stats(bm)

        if props.fx_remove_doubles:
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=props.weld_threshold)
        if props.fx_delete_loose:
            geom = ([v for v in bm.verts if len(v.link_edges) == 0]
                    + [e for e in bm.edges if len(e.link_faces) == 0])
            if geom:
                bmesh.ops.delete(bm, geom=geom, context='VERTS')
        if props.fx_delete_interior:
            faces = [f for f in bm.faces
                     if all(len(l.edge.link_faces) > 1 for l in f.loops)]
            if faces:
                bmesh.ops.delete(bm, geom=faces, context='FACES')
        if props.fx_dissolve_degenerate:
            bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=props.weld_threshold)
        if props.fx_fill_holes:
            edges = [e for e in bm.edges if e.is_boundary]
            sides = props.max_hole_sides if props.max_hole_sides > 0 else BIG
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=sides)
        if props.fx_recalc_normals:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

        bmesh.update_edit_mesh(me)
        after = _mesh_stats(bm)
        _store_stats(context, after)
        self.report({'INFO'} if after["watertight"] else {'WARNING'},
                    "Holes: {} -> {} | Non-manifold: {} -> {} | Watertight: {}".format(
                        before["holes"], after["holes"],
                        before["nonmanifold_edges"], after["nonmanifold_edges"],
                        "YES" if after["watertight"] else "NO"))
        return {'FINISHED'}


class HULLWT_Props(bpy.types.PropertyGroup):
    analyzed: bpy.props.BoolProperty(default=False)
    stat_verts: bpy.props.IntProperty(default=0)
    stat_edges: bpy.props.IntProperty(default=0)
    stat_faces: bpy.props.IntProperty(default=0)
    stat_holes: bpy.props.IntProperty(default=0)
    stat_hole_edges: bpy.props.IntProperty(default=0)
    stat_largest_hole: bpy.props.IntProperty(default=0)
    stat_nonmanifold: bpy.props.IntProperty(default=0)
    stat_wire: bpy.props.IntProperty(default=0)
    stat_loose_verts: bpy.props.IntProperty(default=0)
    stat_interior: bpy.props.IntProperty(default=0)
    stat_degenerate: bpy.props.IntProperty(default=0)
    stat_parts: bpy.props.IntProperty(default=0)
    is_watertight: bpy.props.BoolProperty(default=False)

    weld_threshold: bpy.props.FloatProperty(
        name="Merge Distance",
        description="Distance below which vertices are welded together",
        default=0.0001, min=0.0, soft_max=1.0, precision=5, subtype='DISTANCE')
    max_hole_sides: bpy.props.IntProperty(
        name="Max Hole Size (edges)",
        description="Only fill holes with at most this many boundary edges. 0 = fill all holes",
        default=0, min=0, soft_max=200)
    fill_selected_only: bpy.props.BoolProperty(
        name="Only Selected",
        description="Only fill holes whose boundary edges are selected",
        default=False)
    triangulate_fill: bpy.props.BoolProperty(
        name="Triangulate Fill",
        description="Triangulate the newly created faces",
        default=False)

    fx_remove_doubles: bpy.props.BoolProperty(name="Merge by Distance", default=True)
    fx_delete_loose: bpy.props.BoolProperty(name="Delete Loose", default=True)
    fx_delete_interior: bpy.props.BoolProperty(name="Delete Interior Faces", default=True)
    fx_dissolve_degenerate: bpy.props.BoolProperty(name="Dissolve Degenerate", default=True)
    fx_fill_holes: bpy.props.BoolProperty(name="Fill Holes", default=True)
    fx_recalc_normals: bpy.props.BoolProperty(name="Recalc Normals", default=True)


class HULLWT_PT_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hull Fix"
    bl_label = "Hull Watertight Repair"

    def draw(self, context):
        layout = self.layout
        props = context.scene.hull_wt

        box = layout.box()
        box.label(text="Analysis", icon='VIEWZOOM')
        box.operator("mesh.hullwt_analyze", icon='FILE_REFRESH')
        if props.analyzed:
            col = box.column(align=True)
            col.label(text="Vertices: {}".format(props.stat_verts))
            col.label(text="Faces: {}".format(props.stat_faces))
            col.label(text="Holes: {} ({} edges, largest {})".format(
                props.stat_holes, props.stat_hole_edges, props.stat_largest_hole))
            col.label(text="Non-manifold edges: {}".format(props.stat_nonmanifold))
            col.label(text="Wire edges: {}".format(props.stat_wire))
            col.label(text="Loose verts: {}".format(props.stat_loose_verts))
            col.label(text="Interior faces: {}".format(props.stat_interior))
            col.label(text="Degenerate edges: {}".format(props.stat_degenerate))
            col.label(text="Islands: {}".format(props.stat_parts))
            if props.is_watertight:
                col.label(text="Watertight: YES", icon='CHECKMARK')
            else:
                col.label(text="Watertight: NO", icon='ERROR')

        box = layout.box()
        box.label(text="Inspect", icon='RESTRICT_SELECT_OFF')
        row = box.row(align=True)
        row.operator("mesh.hullwt_select_boundary", text="Hole Edges")
        row.operator("mesh.hullwt_select_nonmanifold", text="Non-Manifold")

        box = layout.box()
        box.label(text="Step by Step Repair", icon='TOOL_SETTINGS')
        col = box.column(align=True)
        col.prop(props, "weld_threshold")
        col.operator("mesh.hullwt_remove_doubles", icon='AUTOMERGE_ON')
        col.operator("mesh.hullwt_delete_loose", icon='X')
        col.operator("mesh.hullwt_delete_interior", icon='XRAY')
        col.operator("mesh.hullwt_dissolve_degenerate", icon='X')

        box = layout.box()
        box.label(text="Fill Holes", icon='ADD')
        col = box.column(align=True)
        col.prop(props, "max_hole_sides")
        col.prop(props, "fill_selected_only")
        col.prop(props, "triangulate_fill")
        col.operator("mesh.hullwt_fill_holes", icon='ADD')
        col.operator("mesh.hullwt_recalc_normals", icon='NORMALS_FACE')

        box = layout.box()
        box.label(text="One-Click", icon='MODIFIER')
        col = box.column(align=True)
        col.prop(props, "fx_remove_doubles")
        col.prop(props, "fx_delete_loose")
        col.prop(props, "fx_delete_interior")
        col.prop(props, "fx_dissolve_degenerate")
        col.prop(props, "fx_fill_holes")
        col.prop(props, "fx_recalc_normals")
        col.separator()
        col.operator("mesh.hullwt_watertight_fix", icon='CHECKMARK')


classes = (
    HULLWT_OT_analyze,
    HULLWT_OT_select_boundary,
    HULLWT_OT_remove_doubles,
    HULLWT_OT_delete_loose,
    HULLWT_OT_delete_interior,
    HULLWT_OT_dissolve_degenerate,
    HULLWT_OT_fill_holes,
    HULLWT_OT_recalc_normals,
    HULLWT_OT_select_nonmanifold,
    HULLWT_OT_watertight_fix,
    HULLWT_Props,
    HULLWT_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hull_wt = bpy.props.PointerProperty(type=HULLWT_Props)


def unregister():
    del bpy.types.Scene.hull_wt
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
