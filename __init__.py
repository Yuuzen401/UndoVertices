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
    "version": (0, 0, 2),
    "blender": (2, 80, 0),
    "location":  "Mesh Edit > Sidebar > Undo Vertices",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://github.com/Yuuzen401/UndoVertices",
    "category": "Mesh"
}

import bpy
import gpu
import bgl
import bmesh
import mathutils
import math
import numpy as np
import time

from pprint import pprint
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, PointerProperty, EnumProperty
from gpu_extras.batch import batch_for_shader
from .helper import *
from .usecase import get_curve_map_locations, get_distance
from .preferences import *
from .exception import *
from .mesh_helpers import *

# 作業用の一時モディファイアの名前
modifier_name = '__UndoVerticesWorkingTemporaryModifier__'

class UndoVerticesPropertyGroup(bpy.types.PropertyGroup):
    method_enums = [
        ("Constant", "Constant", "Constant", "NOCURVE", 1),
        ("Curve", "Curve", "Curve", "FCURVE", 2),
    ]
    lock_axiz_enums = [
        ("X", "X", ""),
        ("Y", "Y", ""),
        ("Z", "Z", ""),
    ]

    # 変更方法
    method : EnumProperty(items = method_enums, name = "Method", default = "Constant")
    # 一定の変更率
    constant_rate : IntProperty(name = "Constant Rate", default = 0, min = 0, max = 100)
    # 軸の固定
    lock : EnumProperty(items = lock_axiz_enums, name = "lock axiz", options={'ENUM_FLAG'})

class UndoVerticesSaveVertices():
    # 保存する頂点
    save_selected_verts = None
    save_selected_coords = []
    save_all_len = 0

    @classmethod
    def is_save(self):
        return True if UndoVerticesSaveVertices.save_selected_verts else False

    @classmethod
    def get_len_save_vertices(self):
        return 0 if self.save_selected_verts is None else len(self.save_selected_verts)

    @classmethod
    def set_selected_verts(self, bm):
        self.save_selected_verts = [(v.co.copy(), v.normal.copy(), v.index) for v in bm.verts if v.select]

    @classmethod
    def set_selected_coords(self, bm, obj):
        self.save_selected_coords = []
        verts_co = [v.co.copy() for v in bm.verts if v.select]
        for v_co in verts_co:
            v_co = obj.matrix_world @ v_co
            self.save_selected_coords.append(v_co + obj.location)
        

class UndoVerticesSaveVerticesOperator(bpy.types.Operator):
    bl_idname = "save_verts.operator"
    bl_label = "Undo Vertices Save Vertices"

    def execute(self, context):
        obj = bpy.context.active_object
        bm = bmesh_from_object(obj)
        UndoVerticesSaveVertices.set_selected_verts(bm)

        # 未選択の場合
        if 1 > UndoVerticesSaveVertices.get_len_save_vertices():
            UndoVerticesSaveVertices.save_selected_verts = None
            show_message_error("頂点が選択されていません。")
            return {'CANCELLED'}

        UndoVerticesSaveVertices.set_selected_coords(bm, obj)
        UndoVerticesSaveVertices.save_all_len = len(bm.verts)

        area_3d_view_tag_redraw_all()
        return{'FINISHED'}

class UndoVerticesUndoVerticesOperator(bpy.types.Operator):
    bl_idname = "undo_verts.operator"
    bl_label = "Undo Vertices Control"
    bl_options = {'REGISTER', 'UNDO'}

    # 保存する頂点
    save_selected_verts = None

    @classmethod
    def is_save(self):
        return True if UndoVerticesSaveVertices.save_selected_verts else False

    def draw(self, context):
        prop = context.scene.undo_vertices_prop
        layout = self.layout

        # ---------------------------------------
        box = layout.box()
        row = box.row(align = True)
        row.label(text = "Lock Axis")
        row.scale_y = 2
        row.prop_enum(prop, "lock", "X")
        row.prop_enum(prop, "lock", "Y")
        row.prop_enum(prop, "lock", "Z")
        # ---------------------------------------
        layout.separator()
        box = layout.box()
        row = box.row()
        row.scale_y = 2
        row.prop(prop, 'method')
        # ---------------------------------------
        layout.separator()
        if prop.method == "Constant":
            box = layout.box()
            row = box.row()
            row.scale_y = 2
            row.prop(prop, 'constant_rate', icon = "NOCURVE")
        elif prop.method == "Curve":
            obj = context.active_object
            mod = obj.modifiers[modifier_name]
            layout .template_curve_mapping(mod, 'falloff_curve')

    def execute(self, context):
        prop = context.scene.undo_vertices_prop
        obj = bpy.context.active_object
        me = obj.data
        bm = bmesh_from_object(obj)
        bm.verts.ensure_lookup_table()

        # 頂点数の減っている場合はキャンセルする
        if len(bm.verts) != UndoVerticesSaveVertices.save_all_len:
            show_message_error("頂点数が増減した場合、元に戻すことはできません。")
            return {'CANCELLED'}

        # 頂点数が多すぎる場合は負荷が高いため、タイムアウトによるエラーを検知できるようにする
        start_time = time.time()
        try:
            # カーブによる編集時のみ
            if prop.method == "Curve":
                # 制御用のワープモディファイアを編集時のみ追加
                if obj.modifiers.find(modifier_name) < 0:
                    bpy.ops.object.modifier_add(type = 'WARP')
                    mod = obj.modifiers[-1]
                    mod.name = modifier_name
                    mod.falloff_type = 'CURVE'
                    mod.falloff_curve.use_clip = True

                # drawで実行したマップからカーブの座標を取得する
                locations = get_curve_map_locations(obj.modifiers[modifier_name])

                # 変更前と変更後の距離を取得する
                distance = get_distance(UndoVerticesSaveVertices.save_selected_verts, bm)

                # UI_カーブマッピングをベジェに変換する
                bezier_y = create_bezier_curve(UndoVerticesSaveVertices.get_len_save_vertices(), locations[0], locations[1])
                total = len(bezier_y)
                for v in UndoVerticesSaveVertices.save_selected_verts:
                    save_co = v[0]
                    index = v[2]
                    now_co = bm.verts[index].co

                    for d in distance:
                        if index == d[1]:
                            pos = d[0]
                            break
    
                    pos = int(total * pos) - 1
                    calc_rate = bezier_y[pos]

                    calc_co = get_coord_calc_two_point(save_co, now_co, calc_rate)
                    bm.verts[index].co.x = save_co[0] if "X" in prop.lock else calc_co[0]
                    bm.verts[index].co.y = save_co[1] if "Y" in prop.lock else calc_co[1]
                    bm.verts[index].co.z = save_co[2] if "Z" in prop.lock else calc_co[2]
                    show_message_error_for_timeout(start_time, 3, "処理が長すぎるためキャンセルしました。Saveする頂点を減らしてみてください。")

            elif prop.method == "Constant":
                for v in UndoVerticesSaveVertices.save_selected_verts:
                    save_co = v[0]
                    index = v[2]
                    now_co = bm.verts[index].co
                    calc_co = get_coord_calc_two_point(save_co, now_co, prop.constant_rate / 100)
                    bm.verts[index].co.x = save_co[0] if "X" in prop.lock else calc_co[0]
                    bm.verts[index].co.y = save_co[1] if "Y" in prop.lock else calc_co[1]
                    bm.verts[index].co.z = save_co[2] if "Z" in prop.lock else calc_co[2]
                    show_message_error_for_timeout(start_time, 3, "処理が長すぎるためキャンセルしました。Saveする頂点を減らしてみてください。")

        # タイムアウト例外
        except TimeoutErrorException as e:
            print(e)
            # 強制的に変更率が0の状態に戻す
            prop.method = "Constant"
            prop.constant_rate = 0
            return {'CANCELLED'}

        bmesh.update_edit_mesh(me)
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.mode_set(mode = 'EDIT')

        # 描画中なら全エリアを再描画（アクティブな画面以外も再描画する）
        if UndoVerticesViewVerticesOperator.is_enable():
            area_3d_view_tag_redraw_all()

        return{'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.undo_vertices_prop
        if event:
            prop.method = "Constant"
            prop.constant_rate = 0
       
        return self.execute(context)

class UndoVerticesViewVerticesOperator(bpy.types.Operator):
    bl_idname = "view_verts.operator"
    bl_label = "Undo Vertices Save Vertices"

    # 描画ハンドラ
    draw_handler = None

    @classmethod
    def is_enable(self):
        # 描画ハンドラがNone以外のときは描画中であるため、Trueを返す
        return True if self.draw_handler else False

    @classmethod
    def force_disable(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
        self.draw_handler = None
        area_3d_view_tag_redraw_all()

    @classmethod
    def __handle_add(self, context):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.__draw, (context, ), 'WINDOW', 'POST_VIEW')

    @classmethod
    def __handle_remove(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
        self.draw_handler = None

    @classmethod
    def __draw(self, context):
        if not UndoVerticesSaveVertices.save_selected_coords:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(3)

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (0, 1, 1, 1))
        batch = batch_for_shader(shader, 'POINTS', {"pos": UndoVerticesSaveVertices.save_selected_coords})
        batch.draw(shader)

        bgl.glDisable(bgl.GL_BLEND)

    def invoke(self, context, event):
        prop = context.scene.undo_vertices_prop
        if context.area.type == 'VIEW_3D':
            # enable to disable
            if self.is_enable():
                self.__handle_remove(context)
            # disable to enable
            else:
                self.__handle_add(context)

            # 全エリアを再描画（アクティブな画面以外も再描画する）
            area_3d_view_tag_redraw_all()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class UndoVerticesPanel(bpy.types.Panel):
    bl_label = "Undo Vertices"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Undo Vertices"

    @classmethod
    def poll(self, context):
        if context.mode == 'EDIT_MESH':
            return True
        else:
            UndoVerticesSaveVertices.save_selected_coords = []
            UndoVerticesSaveVertices.save_selected_verts = None
            return False  

    def draw(self, context):
        prop = context.scene.undo_vertices_prop
        bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
        layout = self.layout
        box = layout.box()
        box.label(text = 'Save and Undo vertices')
        row = box.row()
        row.scale_y = 2
        col = row.column()
        col.operator(UndoVerticesSaveVerticesOperator.bl_idname, text = "Save" , text_ctxt = "Save")
        col = row.column()

        if UndoVerticesSaveVertices.is_save() == False:
            col.enabled = False
        elif len(bm.verts) != UndoVerticesSaveVertices.save_all_len:
            col.alert = True
        col.operator(UndoVerticesUndoVerticesOperator.bl_idname, text = "Undo" , text_ctxt = "Undo")

        if UndoVerticesSaveVertices.is_save() == False:
            box.label(text = 'not saved')
        else:
            box.label(text = 'saved vertices : ' + str(UndoVerticesSaveVertices.get_len_save_vertices()))

        layout.separator()
        box = layout.box()
        box.label(text = 'View saved vertices')
        col = box.column()
        col.scale_y = 2
        if UndoVerticesViewVerticesOperator.is_enable():
            col.operator(UndoVerticesViewVerticesOperator.bl_idname, text = "View", depress = True,  icon = "PAUSE") 
        else:
            col.operator(UndoVerticesViewVerticesOperator.bl_idname, text = "View", depress = False, icon = "PLAY")

classes = (
    UndoVerticesPropertyGroup,
    UndoVerticesPanel,
    UndoVerticesSaveVerticesOperator,
    UndoVerticesUndoVerticesOperator,
    UndoVerticesViewVerticesOperator,
    UndoVerticesPreferences,
    UndoVerticesUpdaterPanel,
    )

def register():
    addon_updater_ops.register(bl_info)
    for cls in classes:
        addon_updater_ops.make_annotations(cls)  # Avoid blender 2.8 warnings.
        bpy.utils.register_class(cls)
    bpy.types.Scene.undo_vertices_prop = bpy.props.PointerProperty(type = UndoVerticesPropertyGroup)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.undo_vertices_prop

    addon_updater_ops.unregister()

if __name__ == "__main__":
    register()