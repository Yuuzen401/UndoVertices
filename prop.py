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

from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, FloatVectorProperty, BoolProperty, PointerProperty, EnumProperty
from .undo_vertices import UndoVertices

class UndoVerticesPropertyGroup(PropertyGroup, UndoVertices):
    method_enums = [
        ("Constant", "Constant", "Constant", "NOCURVE", 1),
        ("Curve", "Curve", "Curve", "FCURVE", 2),
    ]
    lock_axiz_enums = [
        ("X", "X", ""),
        ("Y", "Y", ""),
        ("Z", "Z", ""),
    ]
    select_enums = [
        ("SELECT_SET", "", "SELECT_SET", "SELECT_SET", 1),
        ("SELECT_EXTEND", "", "SELECT_EXTEND", "SELECT_EXTEND", 2),
        ("SELECT_SUBTRACT", "", "SELECT_SUBTRACT", "SELECT_SUBTRACT", 3),
        ("SELECT_DIFFERENCE", "", "SSELECT_DIFFERENCE", "SELECT_DIFFERENCE", 4),
        #("SELECT_INTERSECT", "", "SELECT_INTERSECT", "SELECT_INTERSECT", 5),  # 直接選択と違いが無いので不要
    ]

    # 変更方法
    method : EnumProperty(items = method_enums, name = "Method", default = "Constant")
    # 一定の変更率
    constant_rate : IntProperty(name = "Constant Rate", default = 0, min = 0, max = 100)
    # 軸の固定
    lock_axiz : EnumProperty(items = lock_axiz_enums, name = "lock axiz", options={'ENUM_FLAG'})
    # 選択
    select : EnumProperty(items = select_enums, name = "Select", default = "SELECT_SET")