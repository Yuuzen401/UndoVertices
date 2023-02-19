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

import math
import numpy as np

from pprint import pprint
from .helper import *

def get_curve_map_locations(mod, curve_late):
    curve_map = mod.falloff_curve
    curves = curve_map.curves[0]
    map_x = []
    map_y = []
    for i, p in enumerate(curves.points):
        location = curves.points[i].location
        map_x.append(location[0])
        map_y.append(location[1] * curve_late)
    return (map_x, map_y)

def get_distance(verts, bm, roughness, fixed = None):
    # 移動距離を算出し、変化した量で並べる
    distance = []
    if fixed is None:
        for v in verts:
            save_co = v[0]
            index = v[2]
            now_co = bm.verts[index].co
            x1 = save_co.x
            y1 = save_co.y
            z1 = save_co.z
            x2 = now_co.x
            y2 = now_co.y
            z2 = now_co.z
            if x1 == x2 and y1 == y2 and z1 == z2:
                distance.append((0, index))
            else:
                distance.append((distance_3d(x1, y1, z1, x2, y2, z2), index))

    # 固定座標からの移動量で評価する
    else:
        for v in verts:
            index = v[2]
            now_co = bm.verts[index].co
            x1 = fixed[0]
            y1 = fixed[1]
            z1 = fixed[2]
            x2 = now_co.x
            y2 = now_co.y
            z2 = now_co.z
            if x1 == x2 and y1 == y2 and z1 == z2:
                distance.append((0, index))
            else:
                distance.append((distance_3d(x1, y1, z1, x2, y2, z2), index))

    # 最も大きな移動量を持つものを1として並び変える
    distance = sorted(distance)
    distance_sort = []
    total = len(distance)
    for i, d in enumerate(distance):
        dis = d[0]
        index = d[1]
        # 移動量が無い場合は変化量を0にする
        if dis == 0:
            distance_sort.append((0, index))
        
        # 初回ではない かつ 前回と移動量は変化量を同じにする
        elif i != 0:
            bf_dis = distance[i - 1][0]
            # 移動量の差に対して粗さをつけて判断する
            if abs(dis - bf_dis) <= roughness:
                distance_sort.append((distance_sort[-1][0], index))
            else:
                distance_sort.append(((i + 1) / total, index))
        else:
            distance_sort.append(((i + 1) / total, index))

    return distance_sort

# curve_name = "__UndoVerticesWorkingTemporaryCurve__"

# def delete_temporary_curve():
#    if bpy.data.curves.get(curve_name) is not None:
#        bpy.data.curves.remove(bpy.data.curves[curve_name])

# def create_temporary_curve():
#     curve = bpy.data.curves.new(name = curve_name, type="CURVE")
#     curve.dimensions = "2D"
#     curve.use_fake_user = True
#     spline = curve.splines.new("BEZIER")
#     points = spline.bezier_points
    
#     point_start = points[0]
#     point_start.co = (0, 0, 0)
#     point_start.handle_left_type = "VECTOR"
#     point_start.handle_right_type = "VECTOR"

#     points.add(1)
#     point_end = points[-1]
#     point_end.co = (1, 1, 0)
#     point_end.handle_left_type = "VECTOR"
#     point_end.handle_right_type = "VECTOR"
