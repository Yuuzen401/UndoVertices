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

class UndoVertices():
    # 保存する頂点
    save_selected_verts = None
    save_selected_coords = []
    save_all_len = 0

    @classmethod
    def is_save(self):
        return True if UndoVertices.save_selected_verts else False

    @classmethod
    def reset_save(self):
        self.save_selected_coords = []
        self.save_selected_verts = None

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
    def set_selected_coords(self, bm, obj):
        self.save_selected_coords = []
        verts_co = [v.co.copy() for v in bm.verts if v.select]
        for v_co in verts_co:
            v_co = obj.matrix_world @ v_co
            self.save_selected_coords.append(v_co)

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