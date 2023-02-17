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

class UndoVertices():
    # 保存する頂点
    save_selected_verts = None
    save_selected_coords = []
    save_all_len = 0

    @classmethod
    def is_save(self):
        return True if UndoVertices.save_selected_verts else False

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