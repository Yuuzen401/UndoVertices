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

import bmesh
import time
from bpy.types import Operator
from .undo_vertices import UndoVertices
from .helper import *
from .mesh_helpers import *
from .usecase import *

# 作業用の一時モディファイアの名前
modifier_name = '__UndoVerticesWorkingTemporaryModifier__'

class UndoVerticesUndoOperator(Operator, UndoVertices):
    bl_idname = "undo_verts.operator"
    bl_label = "Undo Vertices Control"
    bl_options = {'REGISTER', 'UNDO'}

    # 保存する頂点
    save_selected_verts = None

    @classmethod
    def is_save(self):
        return True if UndoVertices.save_selected_verts else False

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
        if len(bm.verts) != UndoVertices.save_all_len:
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
                distance = get_distance(UndoVertices.save_selected_verts, bm)

                # UI_カーブマッピングをベジェに変換する
                bezier_y = create_bezier_curve(UndoVertices.get_len_save_vertices(), locations[0], locations[1])
                total = len(bezier_y)
                for v in UndoVertices.save_selected_verts:
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
                for v in UndoVertices.save_selected_verts:
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

        return{'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.undo_vertices_prop
        if event:
            prop.method = "Constant"
            prop.constant_rate = 0
       
        return self.execute(context)

def register():
    bpy.utils.register_class(UndoVerticesUndoOperator)

def unregister():
    bpy.utils.unregister_class(UndoVerticesUndoOperator)
