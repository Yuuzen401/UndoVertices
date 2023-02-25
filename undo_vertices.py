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

from .mesh_helpers import *
from .grease_pencil_helpers import *

class UndoVertices():
    # 保存する頂点
    annotation_point_name = "__UndoVerticesWorkingTemporaryAnnotationPoint__"
    annotation_line_name = "__UndoVerticesWorkingTemporaryAnnotationLine__"
    annotation_point_mod_name = "__UndoVerticesWorkingTemporaryAnnotationPointMod__"
    annotation_line_mod_name = "__UndoVerticesWorkingTemporaryAnnotationLineMod__"
    save_selected_verts = None
    save_selected_coords = []
    save_selected_edge_coords = []
    save_selected_coords_mod = []
    save_selected_edge_coords_mod = []
    save_all_len = 0
    annotation_layer_point = None
    annotation_layer_line = None
    annotation_layer_point_mod = None
    annotation_layer_line_mod = None

    @classmethod
    def is_save(self):
        return True if UndoVertices.save_selected_verts else False

    @classmethod
    def reset_save(self, context):
        self.remove_annotation_layer(context)
        self.save_selected_verts = None
        self.save_selected_coords = []
        self.save_selected_edge_coords = []
        self.save_selected_coords_mod = []
        self.save_selected_edge_coords_mod = []
        self.save_all_len = 0
        self.annotation_layer_point = None
        self.annotation_layer_line = None
        self.annotation_layer_point_mod = None
        self.annotation_layer_line_mod = None

    @classmethod
    def get_len_save_verts(self):
        return 0 if self.save_selected_verts is None else len(self.save_selected_verts)

    @classmethod
    def set_selected_verts(self, verts):
        self.save_selected_verts = verts

    @classmethod
    def get_selected_verts(self, bm):
        return [(v.co.copy(), v.normal.copy(), v.index) for v in bm.verts if v.select]

    @classmethod
    def set_selected_coords(self):
        self.save_selected_coords = []
        self.save_selected_edge_coords = []
        self.save_selected_coords_mod = []
        self.save_selected_edge_coords_mod = []
        obj = bpy.context.active_object

        bm = bmesh_from_object(obj)
        bm.select_flush(True)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.select = False
        for v in self.save_selected_verts:
            index = v[2]
            bm.verts[index].select = True
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)

        bm = bmesh_copy_from_object(obj, True, False, False)

        # 表示する頂点を設定する
        verts_co = [v.co.copy() for v in bm.verts if v.select]
        for v_co in verts_co:
            self.save_selected_coords.append(v_co)

        # 表示するエッジを設定する
        edges = [e for e in bm.edges if e.select]
        for e in edges:
            co_1 = e.verts[0].co.copy()
            co_2 = e.verts[1].co.copy()
            self.save_selected_edge_coords.append((co_1, co_2))

        bm_mod = bmesh_copy_from_object(obj, True, False, True)

        # 表示する頂点を設定する
        verts_co = [v.co.copy() for v in bm_mod.verts if v.select]
        for v_co in verts_co:
            self.save_selected_coords_mod.append(v_co)

        # 表示するエッジを設定する
        edges = [e for e in bm_mod.edges if e.select]
        for e in edges:
            co_1 = e.verts[0].co.copy()
            co_2 = e.verts[1].co.copy()
            self.save_selected_edge_coords_mod.append((co_1, co_2))
           
    @classmethod
    def init_annotation_layer(self, context):
        self.remove_annotation_layer(context)
        layer = get_gp_layer(context, self.annotation_line_name)
        layer.color = (0, 1, 1)
        layer.annotation_opacity = 0.2
        layer.thickness = 5
        self.annotation_layer_line = layer

        layer = get_gp_layer(context, self.annotation_point_name)
        layer.color = (0, 1, 1)
        layer.annotation_opacity = 0.5
        layer.thickness = 7
        self.annotation_layer_point = layer

        layer = get_gp_layer(context, self.annotation_line_mod_name)
        layer.color = (0, 0.5, 0)
        layer.annotation_opacity = 1
        layer.thickness = 1
        self.annotation_layer_line_mod = layer

        layer = get_gp_layer(context, self.annotation_point_mod_name)
        layer.color = (0, 0.5, 0)
        layer.annotation_opacity = 1
        layer.thickness = 3
        self.annotation_layer_point_mod = layer

    @classmethod
    def remove_annotation_layer(self, context):
        gp = context.scene.grease_pencil
        if gp is not None:
            for layer in list(gp.layers) :
                if self.annotation_point_name or self.annotation_line_name or self.annotation_point_mod_name or self.annotation_line_mod_name in layer.info :
                    gp.layers.remove( layer )

    @classmethod
    def save_to_annotation(self, context):
        self.init_annotation_layer(context)
        frame = get_gp_frame(self.annotation_layer_line)
        for e in self.save_selected_edge_coords :
            stroke = frame.strokes.new()
            stroke.points.add(1)
            stroke.points[-1].co = e[0]
            stroke.points.add(1)
            stroke.points[-1].co = e[1]
            stroke.points.update()

        frame = get_gp_frame(self.annotation_layer_point)
        for v in self.save_selected_coords :
            stroke = frame.strokes.new()
            stroke.points.add(1)
            stroke.points[-1].co = v
            stroke.points.update()

        frame = get_gp_frame(self.annotation_layer_line_mod)
        for e in self.save_selected_edge_coords_mod :
            stroke = frame.strokes.new()
            stroke.points.add(1)
            stroke.points[-1].co = e[0]
            stroke.points.add(1)
            stroke.points[-1].co = e[1]
            stroke.points.update()

        frame = get_gp_frame(self.annotation_layer_point_mod)
        for v in self.save_selected_coords_mod :
            stroke = frame.strokes.new()
            stroke.points.add(1)
            stroke.points[-1].co = v
            stroke.points.update()

        self.toggle_annotation_view()

    @classmethod
    def toggle_annotation_view(self):
        if self.annotation_layer_point is not None:
            prop = bpy.context.scene.undo_vertices_prop
            self.annotation_layer_point.hide = False == (prop.is_view and prop.is_view_point and prop.is_modifier == False)
            self.annotation_layer_line.hide = False == (prop.is_view and prop.is_view_line and prop.is_modifier == False)
            self.annotation_layer_point_mod.hide = False == (prop.is_view and prop.is_view_point and prop.is_modifier == True)
            self.annotation_layer_line_mod.hide = False == (prop.is_view and prop.is_view_line and prop.is_modifier == True)

    @classmethod
    def is_len_diff(self):
        bm = bmesh_from_object(bpy.context.active_object)
        return self.save_all_len == len(bm.verts)

    @classmethod
    def select_save_verts(self, context, obj):
        prop = context.scene.undo_vertices_prop
        bm = bmesh_from_object(obj)
        bm.select_flush(True)
        bm.verts.ensure_lookup_table()

        # 保存した頂点のみ選択する
        if prop.select == "SELECT_SET":
            for v in bm.verts:
                v.select = False
            for v in self.save_selected_verts:
                index = v[2]
                bm.verts[index].select = True

        # 保存した頂点を追加選択する
        elif prop.select == "SELECT_EXTEND":
            for v in self.save_selected_verts:
                index = v[2]
                bm.verts[index].select = True

        # 保存した頂点を対象に選択を解除する
        elif prop.select == "SELECT_SUBTRACT":
            for v in self.save_selected_verts:
                index = v[2]
                bm.verts[index].select = False

        # # 保存済の頂点を対象に選択状態を反転する
        elif prop.select == "SELECT_DIFFERENCE":
            for v in self.save_selected_verts:
                index = v[2]
                # 選択したものに対して選択状態を反転する
                bm.verts[index].select = bm.verts[index].select != True
            
        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)