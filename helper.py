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
import bmesh
import math
import numpy as np
import time
from .exception import *

def is_mesh_edit(obj):
    return obj and obj.mode == "EDIT" and obj.type == "MESH"

def area_3d_view_tag_redraw_all():
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()

# アクティブなエリアのSpaceView3Dを取得する
def get_space_view_3d():
    aria = bpy.context.area
    for space in aria.spaces:
        if space.type == "VIEW_3D":
            return space
    else:
        return None

# VIEW3Dの視点から、法線が内側であるか
def is_in_normal_from_view_3d(context, normal):
    space_view_3d = get_space_view_3d()
    matrix_z = space_view_3d.region_3d.view_rotation.to_matrix().col[2]
    return normal.dot(matrix_z) < 0

def show_message_info(message):
    def draw(self, context):
        self.layout.label(text = message)
    bpy.context.window_manager.popup_menu(draw, title = "Message", icon = "INFO")

def show_message_error(message):
    def draw(self, context):
        self.layout.label(text = message)
    bpy.context.window_manager.popup_menu(draw, title = "Error", icon = "ERROR")

def is_timeout(start_time, error_sec):
    """タイムアウトを判断する
    """
    return time.time() - start_time > error_sec

def show_message_error_for_timeout(start_time, error_sec, message):
    """タイムアウトエラーによるメッセージを出力する
    """
    if is_timeout(start_time, error_sec):
        show_message_error(message)
        raise TimeoutErrorException(message)

def get_coord_calc_two_point(p1, p2, progress):
    """始点と終点からの進んだ割合を与えた場合の座標を取得する

    :param int p1 始点
    :param int p2 終点
    :param float progress 0 ~ 1
    :return tuple (x, y, z)
    """
    return tuple(p1[i] + (p2[i] - p1[i]) * progress for i in range(3))

def get_avg_location(verts):
    """複数の頂点から平均座標を求める
    """
    total_x = 0
    total_y = 0
    total_z = 0
    for v in verts:
        total_x += v.co.x
        total_y += v.co.y
        total_z += v.co.z
    num_verts = len(verts)
    avg_x = total_x / num_verts
    avg_y = total_y / num_verts
    avg_z = total_z / num_verts
    return (avg_x, avg_y, avg_z)

def distance_3d(x1, y1, z1, x2, y2, z2):
    """3次元上での頂点と頂点の距離を求める
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)


def get_euler_calc_two_3d_point(co1, co2):
    """二つの3D座標を辺と見立ててオイラー角を取得する

    :param Vector co1 座標
    :param Vector co2 座標
    :return tuple (x角度, y角度, z角度)
    """
    bm = bmesh.new()
    v1 = bm.verts.new(co1)
    v2 = bm.verts.new(co2)
    # エッジの向きを取得する
    vec = v2.co - v1.co
    # オイラー角を取得する
    euler = vec.to_track_quat("Z", "Y").to_euler()
    x = round(math.degrees(euler.x), 2)
    y = round(math.degrees(euler.y), 2)
    z = round(math.degrees(euler.z), 2)
    bm.free()
    return (x, y, z)

def euler_angle_to_end_point(x, y, z, length):    
    phi = math.radians(x)
    theta = math.radians(y)
    psi = math.radians(z)
    x = length * math.cos(phi) * math.sin(theta) * math.cos(psi)
    y = length * math.cos(phi) * math.sin(theta) * math.sin(psi)
    z = length * math.cos(phi) * math.cos(theta)
    return (x, y, z)

def match_3d_euler(euler1, euler2, diff_value):
    match_x = abs(euler1[0] - euler2[0]) < diff_value
    match_y = abs(euler1[1] - euler2[1]) < diff_value
    match_z = abs(euler1[2] - euler2[2]) < diff_value
    return match_x == True and match_y == True and match_z == True

def create_bezier_curve(segment, x_data = [0, 1], y_data = [0 , 1]):
    """2Dのベジェ曲線を作る
    """
    t = np.linspace(0, 1, len(x_data))
    t_fit = np.linspace(0, 1, segment + 10)
    # x_fit = np.interp(t_fit, t, x_data)
    y_fit = np.interp(t_fit, t, y_data)

    # 本処理ではy座標だけ欲しいのでコメントアウトしてy座標を取得する
    return y_fit

    # vector = np.array([x_fit, y_fit])
    # vector = np.transpose(vector)
    # return vector

# 減衰計算
# def calc_decay_rate(start_point, end_point):
#     x1 = start_point[0]
#     y1 = start_point[1]
#     x2 = end_point[0]
#     y2 = end_point[1]

#     m = (y2 - y1) / (x2 - x1)
#     # inf を 2.718281828459045 に変換する
#     decay = np.exp(m)
#     return np.nan_to_num(decay, 2.718281828459045)

# def correction_napier_number(number):
#     """ネイピア数を1として補正する
#     """
#     return number / 2.718281828459045
