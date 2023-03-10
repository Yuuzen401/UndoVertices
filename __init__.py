# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "UndoVertices",
    "description": "undo the vertex",
    "author": "Yuuzen401",
    "version": (0, 0, 18),
    "blender": (2, 80, 0),
    "location":  "Mesh Edit > Sidebar > Undo Vertices",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://github.com/Yuuzen401/UndoVertices",
    "category": "Mesh"
}

import bpy
import bmesh

from bpy.types import Operator, Panel
from pprint import pprint
from .helper import *
from .usecase import get_curve_map_locations, get_distance
from .preferences import *
from .exception import *
from .mesh_helpers import *
from .grease_pencil_helpers import *
from .undo_vertices import UndoVertices
from .view_operator import *
from .undo_operator import *
from .prop import UndoVerticesPropertyGroup

class UndoVerticesSaveOperator(Operator, UndoVertices):
    bl_idname = "save_verts.operator"
    bl_label = "Save vertices"
    bl_options = {"REGISTER", "UNDO"}

    draw_handler = None

    def execute(self, context):
        obj = context.active_object
        bm = bmesh_from_object(obj)
        selected_verts = UndoVertices.get_selected_verts(bm)

        # 未選択の場合
        if 1 > len(selected_verts):
            show_message_error("頂点が選択されていません。")
            return {"CANCELLED"}

        UndoVertices.set_selected_verts(selected_verts)
        # UndoVertices.set_selected_coords(bm, obj)
        UndoVertices.save_all_len = len(bm.verts)
        # UndoVertices.save_to_annotation(context)

        # 保存した頂点で再選択して更新してからBMをコピーする
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = False
        for v in self.save_selected_verts:
            index = v[2]
            bm.verts[index].select = True

        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

        # モディファイア適用無の状態で保存
        bm_copy = bmesh_copy_from_object(obj, True, False, False)
        for v in bm_copy.verts:
            if v.select == False :
                bm_copy.verts.remove(v)
        bm_copy.verts.index_update()
        UndoVertices.save_bm = bm_copy

        # モディファイア適用有の状態で保存
        bm_copy = bmesh_copy_from_object(obj, True, False, True)
        for v in bm_copy.verts:
            if v.select == False :
                bm_copy.verts.remove(v)
        bm_copy.verts.index_update()
        UndoVertices.save_bm_mod = bm_copy

        area_3d_view_tag_redraw_all()
        UndoVertices.active_obj_name = obj.name
        self.__handle_add(context)
        return {"FINISHED"}

    @classmethod
    def __handle_add(self, context):
        if self.draw_handler is None :
            self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.__draw, (context, ), "WINDOW", "POST_VIEW")

    @classmethod
    def __handle_remove(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
        self.draw_handler = None

    @classmethod
    def __draw(self, context):
        now_active_name = context.active_object.name
        if UndoVertices.active_obj_name != now_active_name:
            UndoVertices.reset_save(context)
            UndoVerticesUndoOperator.remove_working_temporary_modifier()
            self.__handle_remove(context)
            area_3d_view_tag_redraw_all()

        elif context.mode != "EDIT_MESH":
            UndoVerticesUndoOperator.remove_working_temporary_modifier()

class UndoVerticesSelectOperator(Operator, UndoVertices):
    bl_idname = "select_verts.operator"
    bl_label = "Save vertices select"

    def execute(self, context):
        # 頂点数が減っている場合はキャンセルする
        if UndoVertices.is_len_diff() == False:
            show_message_error("頂点数が増減した場合、選択できません。")
            return {"CANCELLED"}
        UndoVertices.select_save_verts(context, bpy.context.active_object)
        return{"FINISHED"}

class UndoVerticesResetOperator(Operator, UndoVertices):
    bl_idname = "reset_verts.operator"
    bl_label = "Save vertices reset"

    def execute(self, context):
        UndoVertices.reset_save(context)
        UndoVerticesUndoOperator.remove_working_temporary_modifier()
        return{"FINISHED"}

class VIEW3D_PT_UndoVerticesPanel(Panel, UndoVertices):
    bl_label = "Undo Vertices"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Undo Vertices"

    @classmethod
    def poll(self, context):
        if context.mode == "EDIT_MESH":
            return True

    def draw(self, context):
        prop = context.scene.undo_vertices_prop
        bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
        layout = self.layout

        # Save
        box = layout.box()
        box.label(text = "Save and Undo vertices")
        row = box.row()
        row.scale_y = 2
        col = row.column()
        col.operator(UndoVerticesSaveOperator.bl_idname, text = "Save" , text_ctxt = "Save")
        col = row.column()

        # Undo
        if UndoVertices.is_save() == False:
            col.enabled = False
        elif len(bm.verts) != UndoVertices.save_all_len:
            col.alert = True
        col.operator(UndoVerticesUndoOperator.bl_idname, text = "Undo" , text_ctxt = "Undo")

        if UndoVertices.is_save() == False:
            box.label(text = "not saved")
        else:
            box.label(text = "saved vertices : " + str(UndoVertices.get_len_save_verts()))
            box.operator(UndoVerticesResetOperator.bl_idname, text = "Reset Save" , text_ctxt = "Reset Save")

        # Select
        layout.separator()
        box = layout.box()
        box.label(text = "Select saved vertices")

        row = box.row(align = True)
        row.prop_enum(prop, "select", "SELECT_SET")
        row.prop_enum(prop, "select", "SELECT_EXTEND")
        row.prop_enum(prop, "select", "SELECT_SUBTRACT")
        row.prop_enum(prop, "select", "SELECT_DIFFERENCE")

        col = box.column()
        col.scale_y = 2
        if UndoVertices.is_save() == False:
            col.enabled = False
        elif UndoVertices.is_len_diff() == False:
            col.alert = True
        col.operator(UndoVerticesSelectOperator.bl_idname, text = "Save To Select ") 

        # View
        layout.separator()
        box = layout.box()
        box.label(text = "View saved vertices")
        col = box.column()
        col.scale_y = 2
        if UndoVerticesViewOperator.is_enable():
        # if prop.is_view:
            col.operator(UndoVerticesViewOperator.bl_idname, text = "View", depress = True,  icon = "PAUSE") 
        else:
            col.operator(UndoVerticesViewOperator.bl_idname, text = "View", depress = False, icon = "PLAY")
        row = box.row(align = True)
        row.scale_y = 1.5
        row.prop(prop, "is_view_point", text = "Point")
        row.prop(prop, "is_view_line", text = "Line")
        row = box.row()
        row.scale_y = 1.5
        row.prop(prop, "is_modifier", text = "Modifiers when saved", icon = "MODIFIER")

classes = (
    UndoVerticesPropertyGroup,
    VIEW3D_PT_UndoVerticesPanel,
    UndoVerticesSaveOperator,
    UndoVerticesSelectOperator,
    UndoVerticesResetOperator,
    # UndoVerticesUndoOperator,
    # UndoVerticesViewOperator,
    UndoVerticesPreferences,
    UndoVerticesUpdaterPanel,
    )

def register():
    addon_updater_ops.register(bl_info)
    for cls in classes:
        addon_updater_ops.make_annotations(cls)  # Avoid blender 2.8 warnings.
        bpy.utils.register_class(cls)
    bpy.types.Scene.undo_vertices_prop = bpy.props.PointerProperty(type = UndoVerticesPropertyGroup)
    view_operator.register()
    undo_operator.register()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.undo_vertices_prop

    addon_updater_ops.unregister()
    view_operator.unregister()
    undo_operator.unregister()

if __name__ == "__main__":
    register()