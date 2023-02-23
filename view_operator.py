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

import bpy
import gpu
import bgl
import bmesh
from gpu_extras.batch import batch_for_shader
from bpy.types import Operator
from .undo_vertices import UndoVertices

from .helper import *

class UndoVerticesViewOperator(Operator, UndoVertices):
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
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
        self.draw_handler = None
        area_3d_view_tag_redraw_all()

    @classmethod
    def __handle_add(self, context):
        self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.__draw, (context, ), "WINDOW", "POST_VIEW")

    @classmethod
    def __handle_remove(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, "WINDOW")
        self.draw_handler = None

    @classmethod
    def __draw(self, context):
        if not UndoVertices.save_selected_coords:
            return

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glLineWidth(3)

        shader = gpu.shader.from_builtin("3D_UNIFORM_COLOR")
        shader.bind()
        shader.uniform_float("color", (0, 1, 1, 1))
        batch = batch_for_shader(shader, "POINTS", {"pos" : UndoVertices.save_selected_coords})
        batch.draw(shader)

        bgl.glDisable(bgl.GL_BLEND)

    def invoke(self, context, event):
        prop = context.scene.undo_vertices_prop
        if context.area.type == "VIEW_3D":
            # enable to disable
            # if prop.is_view:
            #     prop.is_view = False
            #     UndoVertices.toggle_annotation_view()

            # # disable to enable
            # else:
            #     prop.is_view = True
            #     UndoVertices.toggle_annotation_view()

            # enable to disable
            if self.is_enable():
                self.__handle_remove(context)
            # disable to enable
            else:
                self.__handle_add(context)

            # 全エリアを再描画（アクティブな画面以外も再描画する）
            area_3d_view_tag_redraw_all()
            return {"FINISHED"}
        else:
            return {"CANCELLED"}

def register():
    bpy.utils.register_class(UndoVerticesViewOperator)

def unregister():
    bpy.utils.unregister_class(UndoVerticesViewOperator)
