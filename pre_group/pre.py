import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import numpy as np

import multiprocessing.dummy as threading  # 多线程池（共享内存）

import pandas as pd


from Element.ElementFactory import ElementFactory

from datetime import datetime

import Face.Face as Face

from Node.node import Node
from Element.BaseElement import Element
from basemethod.base_method import read_and_clean_file,read_and_clean_file_to_values

from multiprocessing import Pool, cpu_count

import psutil  # 用于内存监控（可选，便于调试）
from concurrent.futures import ThreadPoolExecutor, as_completed

from typing import List, Dict, Callable, Optional, Union

# from numba import jit
import datetime
# import threading as th
import multiprocessing

# from pre_group import element


def read_grid_file_01(filename):
    start_time = time.time()  # 记录开始时间

    nodes = []
    elements = []
    element_map = {}
    node_map = {}
    encodings = ['utf-8', 'gbk', 'latin1', 'utf-16']
    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding) as file:
                content = file.read()
            print(f"成功使用 {encoding} 编码打开文件。")
            lines = content.splitlines()
            break
        except UnicodeDecodeError:
            print(f"使用 {encoding} 编码打开文件失败，尝试下一种编码...")
    else:
        print("尝试了所有编码格式，仍无法打开文件，请检查文件是否损坏。")
        return [], [], {}, {}

    in_node_section = False
    in_element_section = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line == "node":
            in_node_section = True
            in_element_section = False
            continue
        if line == "end node":
            in_node_section = False
            print("节点读取完成！")
            continue
        if line == "element":
            in_element_section = True
            in_node_section = False
            continue
        if line == "end element":
            in_element_section = False
            print("单元读取完成！")
            continue

        if in_node_section:
            parts = list(map(float, line.split()))
            node_id = int(parts[0])
            x, y, z = parts[1:4]
            ux, uy, uz, press, rx, ry, rz = parts[4:]
            # 假设 Node 类已经定义
            node = Node(node_id, x, y, z, ux, uy, uz, press, rx, ry, rz)
            nodes.append(node)
            node_map[node_id] = node

        if in_element_section:
            parts = list(map(int, line.split()))
            e_id, t_id, c_id, m_id, d_id, f_id = parts[:6]
            point_parts = parts[6:]
            # 假设 ElementFactory 类已经定义
            element = ElementFactory.create_element(e_id, t_id, c_id, m_id, d_id, f_id)
            element.read_points(point_parts, node_map)

            element_map[e_id] = element
            elements.append(element)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"文件读取完成，耗时: {elapsed_time:.4f} 秒")
    return nodes, elements, node_map, element_map

def read_grid_file(filename):
    start_time = time.time()  # 记录开始时间
    nodes = []
    elements = []
    element_map = {}
    node_map = {}
    encodings = ['utf-8', 'gbk', 'latin1', 'utf-16']
    file_obj = None
    encoding_used = None

    # 优化1：先通过小样本测试编码，避免多次完整读取大文件
    for encoding in encodings:
        try:
            with open(filename, 'rb') as f:
                # 读取前1KB样本测试编码
                sample = f.read(1024)
            sample.decode(encoding)  # 测试编码是否可行
            # 编码可行，正式打开文件
            file_obj = open(filename, 'r', encoding=encoding)
            encoding_used = encoding
            print(f"成功使用 {encoding} 编码打开文件。")
            break
        except UnicodeDecodeError:
            print(f"使用 {encoding} 编码打开文件失败，尝试下一种编码...")
        except Exception as e:
            print(f"尝试 {encoding} 时出错: {e}")

    if not file_obj:
        print("尝试了所有编码格式，仍无法打开文件，请检查文件是否损坏。")
        return [], [], {}, {}

    in_node_section = False
    in_element_section = False

    # 优化2：逐行读取（不一次性加载所有行），降低内存占用
    with file_obj:
        for line in file_obj:
            line = line.strip()
            if not line:
                continue

            # 标记区块状态
            if line == "node":
                in_node_section = True
                in_element_section = False
                continue
            if line == "end node":
                in_node_section = False
                print("节点读取完成！")
                continue
            if line == "element":
                in_element_section = True
                in_node_section = False
                continue
            if line == "end element":
                in_element_section = False
                print("单元读取完成！")
                continue

            # 处理节点数据
            if in_node_section:
                parts = line.split()  # 优化：减少map(float)的额外开销
                node_id = int(parts[0])
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                ux, uy, uz = int(parts[4]), int(parts[5]), int(parts[6])
                press, rx, ry, rz = int(parts[7]), int(parts[8]), int(parts[9]), int(parts[10])
                node = Node(node_id, x, y, z, ux, uy, uz, press, rx, ry, rz)
                nodes.append(node)
                node_map[node_id] = node

            # 处理单元数据
            if in_element_section:
                parts = line.split()
                e_id = int(parts[0])
                t_id, c_id, m_id, d_id, f_id = map(int, parts[1:6])
                point_parts = list(map(int, parts[6:]))
                element = ElementFactory.create_element(e_id, t_id, c_id, m_id, d_id, f_id)
                element.read_points(point_parts, node_map)
                element_map[e_id] = element
                elements.append(element)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"文件读取完成，耗时: {elapsed_time:.4f} 秒")

    return nodes, elements, node_map, element_map



def write_grid_file_01(filename, nodes, elements):
    start_time = time.time()  # 记录开始时间
    print("开始文件写出！")
    with open(filename, 'w') as file:
        file.write("node\n")
        for node in nodes:
            node_info = [
                f"{node.node_id:8d}",
                f"{node.x:16.10f}",
                f"{node.y:16.10f}",
                f"{node.z:16.10f}",
                f"{int(node.ux):8d}",
                f"{int(node.uy):8d}",
                f"{int(node.uz):8d}",
                f"{int(node.press):8d}",
                f"{int(node.rx):8d}",
                f"{int(node.ry):8d}",
                f"{int(node.rz):8d}"
            ]
            file.write(' '.join(node_info) + '\n')
        file.write("end node\n")

        file.write("element\n")
        for element in elements:
            element.write_to_file(file)
        file.write("end element\n")
    print("文件写出完成！")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"文件读取完成，耗时: {elapsed_time:.4f} 秒")

def write_grid_file(filename, nodes, elements):
    start_time = time.time()  # 记录开始时间

    print("开始文件写出！")
    # 优化1：增大缓冲区，减少磁盘IO次数（8MB缓冲区）
    with open(filename, 'w', buffering=8*1024*1024) as file:
        # 优化2：批量收集节点内容，一次性写入
        node_lines = ["node"]  # 先放头部标记
        for node in nodes:
            # 优化3：直接拼接字符串，减少列表操作开销
            line = (f"{node.node_id:8d} {node.x:16.8f} {node.y:16.8f} {node.z:16.8f} "
                   f"{int(node.ux):8d} {int(node.uy):8d} {int(node.uz):8d} "
                   f"{int(node.press):8d} {int(node.rx):8d} {int(node.ry):8d} {int(node.rz):8d}")
            node_lines.append(line)
        node_lines.append("end node")
        # 一次性写入所有节点内容
        file.write('\n'.join(node_lines) + '\n')

        # 批量收集单元内容
        element_lines = ["element"]
        for element in elements:
            # 假设Element有生成字符串的方法，避免直接操作文件
            element_lines.append(element.get_write_string())
        element_lines.append("end element")
        # 一次性写入所有单元内容
        file.write('\n'.join(element_lines) + '\n')

    print("文件写出完成！")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"文件读取完成，耗时: {elapsed_time:.4f} 秒")





def print_memory_usage(tag):
    """辅助函数：打印当前内存占用（可选，用于调试）"""
    process = psutil.Process()
    mem_mb = process.memory_info().rss / 1024 / 1024  # 转换为MB
    print(f"[{tag}] 内存占用: {mem_mb:.2f} MB")


def write_grid_file_02(filename, nodes, elements, batch_size=5000):
    """
    超大规模网格文件写入函数
    :param filename: 输出文件路径
    :param nodes: 节点列表（69万+）
    :param elements: 单元列表（300万+）
    :param batch_size: 分小批收集的大小（默认5000，可根据内存调整）
    """
    start_time = time.time()
    print("开始文件写出！")

    # 优化1：8MB大缓冲区（减少磁盘IO），保留原优化
    with open(filename, 'w', buffering=8 * 1024 * 1024, encoding='utf-8') as file:
        # -------------------------- 写入节点部分 --------------------------
        print_memory_usage("开始写入节点前")
        # 先写入节点头部标记
        file.write("node\n")

        total_nodes = len(nodes)
        # 优化2：分小批收集节点内容（避免单个列表缓存70万条数据）
        for batch_idx in range(0, total_nodes, batch_size):
            # 取当前小批节点（切片不复制数据，内存友好）
            current_batch = nodes[batch_idx:batch_idx + batch_size]
            # 临时列表收集当前批次的节点字符串（仅缓存5000条）
            batch_node_lines = []
            for node in current_batch:
                # 优化3：直接拼接字符串（保留原优化，减少列表操作）
                line = (f"{node.node_id:8d} {node.x:16.8f} {node.y:16.8f} {node.z:16.8f} "
                        f"{int(node.ux):8d} {int(node.uy):8d} {int(node.uz):8d} "
                        f"{int(node.press):8d} {int(node.rx):8d} {int(node.ry):8d} {int(node.rz):8d}")
                batch_node_lines.append(line)

            # 批量写入当前小批节点（一次写入5000条，兼顾IO效率和内存）
            file.write('\n'.join(batch_node_lines) + '\n')
            # 优化4：手动释放当前批次内存（强制回收临时列表）
            del batch_node_lines, current_batch
            # 打印进度（可选）
            processed = min(batch_idx + batch_size, total_nodes)
            print(f"节点已写入：{processed}/{total_nodes}（{processed / total_nodes * 100:.1f}%）")

        # 写入节点尾部标记
        file.write("end node\n")
        print_memory_usage("节点写入完成后")
        print(f"节点写入耗时：{time.time() - start_time:.2f} 秒")

        # -------------------------- 写入单元部分 --------------------------
        # 先写入单元头部标记
        file.write("element\n")

        total_elements = len(elements)
        # 优化5：单元同样分小批处理（300万单元分600批，每批5000条）
        for batch_idx in range(0, total_elements, batch_size):
            current_batch = elements[batch_idx:batch_idx + batch_size]
            batch_elem_lines = []
            for elem in current_batch:
                # 复用element的get_write_string()方法（保留原设计）
                batch_elem_lines.append(elem.get_write_string())

            # 批量写入当前小批单元
            file.write('\n'.join(batch_elem_lines) + '\n')
            # 释放内存
            del batch_elem_lines, current_batch
            # 打印进度（可选）
            processed = min(batch_idx + batch_size, total_elements)
            print(f"单元已写入：{processed}/{total_elements}（{processed / total_elements * 100:.1f}%）")

        # 写入单元尾部标记
        file.write("end element\n")
        print_memory_usage("单元写入完成后")

    # 总耗时统计
    elapsed_time = time.time() - start_time
    print(f"\n文件写出完成！总耗时: {elapsed_time:.4f} 秒")
    print(f"总节点数：{len(nodes)}，总单元数：{len(elements)}")

def merge_duplicate_nodes0(elements):
    unique_nodes = []
    node_map = {}

    for element in elements:
        new_points = []
        for point in element.points:
            if point in unique_nodes:
                index = unique_nodes.index(point)
                new_points.append(unique_nodes[index])
            else:
                unique_nodes.append(point)
                new_points.append(point)
        element.points = new_points

    for i, node in enumerate(unique_nodes, start=1):
        node.node_id = i

    return unique_nodes



# def read_cutting_planes_info(filename):
#     """
#     读取切割面信息，切割面用三个面上的点表示，转为原点法向量格式
#     返回一个列表，每个元素为一个元组，元组包含范围信息、材料号列表和切割面信息（原点和法向量）
#     """
#     cutting_planes_info = []
#     cleaned_lines = read_and_clean_file(filename)
#     materials = None
#     if not cleaned_lines:
#         return cutting_planes_info
#     # 最大材料尺寸
#     max_line_size = np.sqrt(3)*float(cleaned_lines.pop(0))
#     # 获取切割面个数
#     num_planes = int(cleaned_lines.pop(0))
#
#     # 获取要裁剪的材料号
#     material_numbers = list(map(int, cleaned_lines.pop(0).split()))
#     if material_numbers[0] > 0:
#         materials = list(map(int, cleaned_lines.pop(0).split()))
#
#     for _ in range(num_planes):
#         # 读取范围信息
#         x_min, x_max = map(float, cleaned_lines.pop(0).split())
#         y_min, y_max = map(float, cleaned_lines.pop(0).split())
#         z_min, z_max = map(float, cleaned_lines.pop(0).split())
#
#         # 读取三个点的坐标
#         point1 = np.array(list(map(float, cleaned_lines.pop(0).split())))
#         point2 = np.array(list(map(float, cleaned_lines.pop(0).split())))
#         point3 = np.array(list(map(float, cleaned_lines.pop(0).split())))
#
#         # 计算法向量
#         v1 = point2 - point1
#         v2 = point3 - point1
#         plane_normal = np.cross(v1, v2)
#         plane_normal = plane_normal / np.linalg.norm(plane_normal)  # 归一化法向量
#         plane_origin = point1  # 取第一个点作为原点
#
#         cutting_planes_info.append(((x_min, x_max, y_min, y_max, z_min, z_max), materials,max_line_size, (plane_origin, plane_normal)))
#
#     return cutting_planes_info,max_line_size
def read_cutting_planes_info(filename):
    """
    读取切割面信息，支持横排/竖排数据，按顺序逐个读取数值
    返回切割面信息列表和最大线尺寸
    """
    cutting_planes_info = []
    # 读取并清洗文件，返回所有有效数值的列表（按顺序）
    all_values = read_and_clean_file_to_values(filename)
    print(all_values)
    if not all_values:
        return cutting_planes_info, 0.0

    # 定义一个迭代器，方便按顺序逐个取数
    value_iter = iter(all_values)

    try:
        # 1. 读取最大材料尺寸（第一个数值）
        max_line_size = np.sqrt(3) * float(next(value_iter))

        # 2. 读取切割面个数
        num_planes = int(next(value_iter))

        # # 3. 读取要裁剪的材料号相关信息
        # # 先读材料号数量标识（原逻辑中的material_numbers[0]）
        # material_flag = int(next(value_iter))
        # materials = None
        # if material_flag > 0:
        #     # 若标识为正，读取后续的材料号（数量由标识决定）
        #     materials = [int(next(value_iter)) for _ in range(material_flag)]

        # 4. 读取每个切割面的信息
        for _ in range(num_planes):
            # 3. 读取要裁剪的材料号相关信息
            # 先读材料号数量标识（原逻辑中的material_numbers[0]）
            material_flag = int(next(value_iter))
            materials = None
            if material_flag > 0:
                # 若标识为正，读取后续的材料号（数量由标识决定）
                materials = [int(next(value_iter)) for _ in range(material_flag)]


            # 范围信息：x_min, x_max, y_min, y_max, z_min, z_max（6个数值）
            x_min = float(next(value_iter))
            x_max = float(next(value_iter))
            y_min = float(next(value_iter))
            y_max = float(next(value_iter))
            z_min = float(next(value_iter))
            z_max = float(next(value_iter))

            # 三个点的坐标（每个点3个数值，共9个数值）
            point1 = np.array([
                float(next(value_iter)),
                float(next(value_iter)),
                float(next(value_iter))
            ])
            point2 = np.array([
                float(next(value_iter)),
                float(next(value_iter)),
                float(next(value_iter))
            ])
            point3 = np.array([
                float(next(value_iter)),
                float(next(value_iter)),
                float(next(value_iter))
            ])

            # 计算法向量和原点（与原逻辑一致）
            v1 = point2 - point1
            v2 = point3 - point1
            plane_normal = np.cross(v1, v2)
            plane_normal = plane_normal / np.linalg.norm(plane_normal) if np.linalg.norm(plane_normal) > 1e-10 else np.zeros(3)
            plane_origin = point1

            cutting_planes_info.append((
                (x_min, x_max, y_min, y_max, z_min, z_max),
                materials,
                max_line_size,
                (plane_origin, plane_normal)
            ))
        # 5. 是否进行边界处理
        is_handle_boundary= float(next(value_iter))
        return cutting_planes_info, max_line_size, is_handle_boundary

    except StopIteration:
        # 处理数据不完整的情况
        print("文件数据不完整，无法读取所有必要信息")
        return cutting_planes_info, 0.0


def get_max_ele_id(elements):
    """
    获取节点列表中的最大节点号
    """

    max_ele_id = 0
    for element in elements:
        max_ele_id = max(max_ele_id, element.e_id)
    return max_ele_id


# def cut_elements(elements, cutting_planes_info, new_element_id,tol):
#     """
#     根据单元形心所在范围和材料号选择相应切割面进行切割
#     """
#     new_elements = []
#     for element in elements:
#         centroid = element.center
#         x, y, z = centroid
#         selected_plane = None
#         for range_info, materials, max_line_size, plane_info in cutting_planes_info:
#             x_min, x_max, y_min, y_max, z_min, z_max = range_info
#             # 检查单元形心是否在范围内且材料号符合要求
#             if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
#                 if not materials or element.m_id in materials:
#                     selected_plane0 = plane_info
#                     plane_origin, plane_normal = selected_plane0
#                     a, b, c = plane_normal
#                     d = - (a * plane_origin[0] + b * plane_origin[1] + c * plane_origin[2])
#                     # 点到平面的距离公式：|a*x + b*y + c*z + d| / sqrt(a² + b² + c²)
#                     numerator = abs(a * x + b * y + c * z + d)
#                     denominator = np.linalg.norm(plane_normal)  # 法向量已归一化，分母=1，可简化为numerator
#                     distance_to_plane = numerator / (denominator + 1e-12)  # 避免分母为0
#
#                     if distance_to_plane <= max_line_size + tol:
#                         selected_plane = selected_plane0
#                         break  # 距离过远，跳过该切割面
#                     # break
#         if selected_plane:
#             # plane_origin, plane_normal = selected_plane
#             positive, negative = element.cut_by_plane(plane_origin, plane_normal, new_element_id,tol)
#             if positive:
#                 positive.clip=1
#                 new_elements.append(positive)
#             if negative:
#                 negative.clip = 1
#                 new_elements.append(negative)
#         else:
#             new_elements.append(element)
#     return new_elements


def in_clip_range(x, y, z, plane_origin, plane_normal,max_line_size):
    """
    根据单元形心所在范围和材料号选择相应切割面进行切割
    """
    a, b, c = plane_normal
    d = - (a * plane_origin[0] + b * plane_origin[1] + c * plane_origin[2])
    # 点到平面的距离公式：|a*x + b*y + c*z + d| / sqrt(a² + b² + c²)
    numerator = abs(a * x + b * y + c * z + d)
    denominator = np.linalg.norm(plane_normal)  # 法向量已归一化，分母=1，可简化为numerator
    distance_to_plane = numerator / (denominator + 1e-12)  # 避免分母为0

    if distance_to_plane <= max_line_size:
        return True
    return False
def cut_elements(elements, cutting_planes_info, new_element_id,tol):
    """
    根据单元形心所在范围和材料号选择相应切割面进行切割
    """
    new_elements = []
    for element in elements:
        centroid = element.center
        x, y, z = centroid
        selected_plane = None
        for range_info, materials, max_line_size, plane_info in cutting_planes_info:
            plane_origin, plane_normal = plane_info
            if in_clip_range(x, y, z, plane_origin, plane_normal,max_line_size):
                element.clip = 2
                x_min, x_max, y_min, y_max, z_min, z_max = range_info
                # 检查单元形心是否在范围内且材料号符合要求
                if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
                    if not materials or element.m_id in materials:
                        selected_plane = plane_info
                        break  # 距离过远，跳过该切割面

        if selected_plane:
            plane_origin, plane_normal = selected_plane
            positive, negative = element.cut_by_plane(plane_origin, plane_normal, new_element_id,tol)
            if positive:
                positive.clip=1
                new_elements.append(positive)
            if negative:
                negative.clip = 1
                new_elements.append(negative)
        else:
            new_elements.append(element)
    return new_elements

def cut_elements_with_face_record(elements, cutting_planes_info, new_element_id,tol):
    """
    根据单元形心所在范围和材料号选择相应切割面进行切割
    """
    face_replace_subdict_list_for_all_element = []

    new_elements = []
    for element in elements:
        centroid = element.center
        x, y, z = centroid
        selected_plane = None
        for range_info, materials, max_line_size, plane_info in cutting_planes_info:
            plane_origin, plane_normal = plane_info
            if in_clip_range(x, y, z, plane_origin, plane_normal,max_line_size):
                element.clip = 2
                x_min, x_max, y_min, y_max, z_min, z_max = range_info
                # 检查单元形心是否在范围内且材料号符合要求
                if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
                    if not materials or element.m_id in materials:
                        selected_plane = plane_info
                        break  # 距离过远，跳过该切割面

        if selected_plane:
            plane_origin, plane_normal = selected_plane
            positive, negative = element.cut_by_plane(plane_origin, plane_normal, new_element_id,tol)

           # 如果切出两个单元，则把他们的
            if positive and negative:
                if element.t_id == 6:
                    element = element.to_element57()
                face_replace_dict1 = Face.compare_element57_faces(element, positive)
                face_replace_dict2 = Face.compare_element57_faces(element, negative)
                merged_face_replace_dict = Face.merge_face_replace_dict(face_replace_dict1, face_replace_dict2, element.e_id)
                face_replace_subdict_list_for_one_element = Face.convert_merged_dict_to_subdict_list(merged_face_replace_dict)
                face_replace_subdict_list_for_all_element = face_replace_subdict_list_for_all_element + face_replace_subdict_list_for_one_element

            if positive:
                positive.clip=1
                new_elements.append(positive)
            if negative:
                negative.clip = 1
                new_elements.append(negative)
        else:
            new_elements.append(element)
    return new_elements, face_replace_subdict_list_for_all_element


#节点压缩重拍-保证原始节点列表不变
def merge_duplicate_nodes(elements, original_nodes, max_original_node_id, precision=8):
    """
    优化版合并重复节点：用哈希表加速匹配，耗时从分钟级降至秒级
    :param elements: 切割后的单元列表
    :param original_nodes: 原始节点字典 {原始ID: 节点对象}
    :param max_original_node_id: 最大原始节点ID
    :param precision: 坐标精度（用于判断重复）
    :return: 合并后的所有节点列表
    """
    # ----------------------
    # 优化1：提前构建原始节点的“坐标键→节点”哈希表（仅计算1次）
    # ----------------------
    # 生成原始节点的坐标键（四舍五入到指定精度，转为元组作为字典键）
    original_coord_map = {}
    for orig_node in original_nodes.values():
        # 提前计算坐标键，避免后续重复计算
        coord_key = (
            round(orig_node.x, precision),
            round(orig_node.y, precision),
            round(orig_node.z, precision)
        )
        # 若存在重复坐标的原始节点，保留第一个（避免覆盖）
        if coord_key not in original_coord_map:
            original_coord_map[coord_key] = orig_node

    # ----------------------
    # 优化2：单轮遍历单元节点，同步处理原始节点匹配和新增节点去重
    # ----------------------
    new_unique_nodes = {}  # 新增节点的“坐标键→节点”哈希表（去重）
    for element in elements:
        processed_points = []
        for point in element.points:
            # 计算当前节点的坐标键（仅1次浮点运算）
            point_coord_key = (
                round(point.x, precision),
                round(point.y, precision),
                round(point.z, precision)
            )

            # 情况1：是原始节点 → 直接取原始节点对象（哈希表O(1)查找）
            if point_coord_key in original_coord_map:
                processed_points.append(original_coord_map[point_coord_key])

            # 情况2：是新增节点 → 去重后加入（哈希表O(1)判断）
            else:
                if point_coord_key not in new_unique_nodes:
                    new_unique_nodes[point_coord_key] = point
                processed_points.append(new_unique_nodes[point_coord_key])

        # 更新单元的节点列表（仅1次赋值）
        element.points = processed_points

    # ----------------------
    # 优化3：快速为新增节点分配ID（仅1次循环）
    # ----------------------
    new_node_list = list(new_unique_nodes.values())
    for idx, node in enumerate(new_node_list, start=1):
        node.node_id = max_original_node_id + idx  # 从最大原始ID+1开始编号

    # ----------------------
    # 合并原始节点和新增节点（保持原始节点顺序）
    # ----------------------
    all_nodes = list(original_nodes.values()) + new_node_list

    return all_nodes,new_node_list


def renumber_element_ids(elements):
    new_elements = [None] * len(elements)
    for i, element in enumerate(elements):
        element.e_id = i + 1
        new_elements[i] = element
    return new_elements



def handle_boundary_element1(elements,new_add_nodes_map,max_line_size):
    new_elements = []

    for element in elements:
        new_element=element.change_boundary_element(new_add_nodes_map,max_line_size)
        new_elements.append(new_element)
    return new_elements

def handle_boundary_element(elements, new_add_nodes_map, max_line_size):
    start = time.time()
    num_threads = multiprocessing.cpu_count()  # 线程数=CPU核心数（和切割保持一致）
    chunk_size = len(elements) // num_threads
    chunk_size = max(chunk_size, 1)  # 最小1个单元/块

    # 1. 分块（和多线程切割的分块逻辑完全一致）
    element_chunks = [elements[i:i + chunk_size] for i in range(0, len(elements), chunk_size)]

    # 2. 定义单块处理函数（内部调用边界处理逻辑，无序列化）
    def process_chunk(chunk):
        """处理单个单元块（多线程共享内存，直接操作对象）"""
        processed_chunk = []
        for element in chunk:
            # 只处理需要边界处理的单元（剪枝，减少无效计算）
            if element.clip in (2, 3):
                # 直接调用原有逻辑，无需序列化（多线程共享内存）
                element = element.change_boundary_element(new_add_nodes_map, max_line_size)
            processed_chunk.append(element)
        return processed_chunk

    # 3. 多线程池（和切割保持一致：用 multiprocessing.dummy 的 ThreadPool）
    import multiprocessing.dummy as threading  # 共享内存的线程池
    pool = threading.Pool(processes=num_threads)
    results = []
    for chunk in element_chunks:
        # 异步提交任务（和切割的 apply_async 风格一致）
        result = pool.apply_async(
            process_chunk,
            args=(chunk,)  # 仅传递块数据，new_add_nodes_map 共享内存
        )
        results.append(result)

    # 4. 等待所有任务完成，收集结果（和切割逻辑一致）
    pool.close()
    pool.join()

    new_elements = []
    for result in results:
        new_elements.extend(result.get())

    # 5. 打印耗时（保持日志风格一致）
    total_time = time.time() - start
    print(f"*************多线程边界处理耗时: {total_time:.2f}s (线程数: {num_threads})")
    return new_elements

def clip_inimesh(input_filename, cutting_planes_filename, output_filename, tolerance):
    start_time = datetime.datetime.now()

    # 1. 读取切割面信息
    cutting_planes_info, max_line_size, is_handle_boundary = read_cutting_planes_info(cutting_planes_filename)
    end_time1 = datetime.datetime.now()

    print(f"读取控制文件时间: {(end_time1 - start_time).total_seconds()} 秒")
    # 2. 读取原始网格（主进程保留原始节点）
    nodes, elements, _, _ = read_grid_file(input_filename)
    # for node in nodes:
    #     if node.node_id == 22393:
    #         print(f"read 后（主进程原始节点）：{id(node)}")  # 原始地址
    original_nodes_map = {node.node_id: node for node in nodes}
    original_elements_map = {elem.e_id: elem for elem in elements}
    max_original_node_id = max(original_nodes_map.keys()) if original_nodes_map else 0
    end_time2 = datetime.datetime.now()
    print(f"读取节点单元时间: {(end_time2 - end_time1).total_seconds()} 秒")

    # 2-1. 如果is_handle_boundary==2,使用面遍历方法处理边界,在此处对网格进行面排序
    # 方法：对每个element进行遍历，再遍历每个单元的每个面
    # 面数据结构：
    unique_faces = []
    unique_face_map = {}
    if is_handle_boundary == 2:
        unique_faces, unique_face_map = Face.create_face_list(elements)
    end_time2_1 = datetime.datetime.now()
    print(f"创建面排序时间: {(end_time2_1 - end_time2).total_seconds()} 秒")

    # 3. 获取最大单元ID
    max_ele_id = get_max_ele_id(elements)
    end_time3 = datetime.datetime.now()
    print(f"最大单元号时间: {(end_time3 - end_time2_1).total_seconds()} 秒")

    # 4. 多线程切割（关键：使用 th.Pool，共享内存）
    num_threads = multiprocessing.cpu_count()  # 线程数通常等于CPU核心数
    chunk_size = len(elements) // num_threads
    chunk_size = max(chunk_size, 1)
    element_chunks = [elements[i:i + chunk_size] for i in range(0, len(elements), chunk_size)]
    # 多线程池（共享内存，节点引用不复制）
    pool = threading.Pool(processes=num_threads)
    results = []
    results_with_face = []
    face_replace_dict_list = []
    face_replace_whole_dict = {}
    if is_handle_boundary == 2:
        for chunk in element_chunks:
            # 子线程直接修改节点属性（共享内存，无需记录）
            result = pool.apply_async(
                cut_elements_with_face_record,  # 多线程版本的切割函数
                args=(chunk, cutting_planes_info, max_ele_id, tolerance)
            )
            results_with_face.append(result)

        for result_with_face in results_with_face:
            result, face_replace_dict_sublist = result_with_face.get()
            results.extend(result)

            face_replace_dict_list.extend(face_replace_dict_sublist)
        face_replace_whole_dict = Face.remove_twice_face(face_replace_dict_list)

        # for dict in face_replace_dict_list:
        #     print("被切割单元")
        #     print(dict['element_id'])
        #     print("被切割面")
        #     print(dict['old_face_nodes'])
    else:
        for chunk in element_chunks:
            # 子线程直接修改节点属性（共享内存，无需记录）
            result = pool.apply_async(
                cut_elements,  # 多线程版本的切割函数
                args=(chunk, cutting_planes_info, max_ele_id, tolerance)
            )
            results.append(result)

    pool.close()
    pool.join()
    end_time4 = datetime.datetime.now()
    print(f"多线程切割时间: {(end_time4 - end_time3).total_seconds()} 秒")

    # 5. 收集切割后的新单元
    new_elements = []
    if is_handle_boundary == 2:
        for result_with_face in results_with_face:
            result, face_replace_dict_sublist = result_with_face.get()
            new_elements.extend(result)
    else:
        for result in results:
            new_elements.extend(result.get())
    end_time5 = datetime.datetime.now()
    print(f"收集结果时间: {(end_time5 - end_time4).total_seconds()} 秒")

    # 5-1. 根据切割过程中收集的face_replace_whole_dict信息中的key值（切割面未切割时的面编号）
    # 用unique_face_map的key值找到对应的面id
    # 再到unique_faces数列中找到这个面的邻居单元id
    # 把这个单元替换成新的57号单元

    # 先整理出来要替换的单元id
    target_element_dict = {}
    for old_face_nodes, sub_dict in face_replace_whole_dict.items():
        unique_face_id = unique_face_map[old_face_nodes]
        unique_face = unique_faces[unique_face_id-1]
        # print(old_face_nodes)
        # print([unique_face.neighbour_cell1, unique_face.neighbour_cell2])
        target_element_id = 0
        if unique_face.neighbour_cell2 == 0:  # 邻居单元2的id为0说明是单面，跳过
            continue
        else:
            neighbour_element_id = sub_dict['element_id']
            if unique_face.neighbour_cell1 == neighbour_element_id:
                target_element_id = unique_face.neighbour_cell2
            else:
                target_element_id = unique_face.neighbour_cell1

            sub_dict['old_face_nodes'] = list(old_face_nodes)
            if target_element_id not in target_element_dict:
                target_element_dict[target_element_id] = [sub_dict]
            else:
                target_element_dict[target_element_id].append(sub_dict)

    # 遍历new_elements,找到e_id在target_element_dict的key中存在的element，进行单元替换
    for idx, element in enumerate(new_elements):
        if element.e_id in target_element_dict:
            # 有多少个子字典就进行多少次替换
            if element.t_id == 6:
                element = element.to_element57()
            new_element = element
            for sub_dict in target_element_dict[element.e_id]:
                # new_element = Face.update_element57_faces(new_element, sub_dict['old_face_nodes'], sub_dict['new_face_nodes1'], sub_dict['new_face_nodes2'])
                old_face_node_list = []
                for node_id in sub_dict['old_face_nodes']:
                    old_face_node_list.append(original_nodes_map[node_id])
                new_add_nodes_map = Face.find_new_nodes(old_face_node_list, sub_dict['new_face_nodes1'], sub_dict['new_face_nodes2'])
                new_element = new_element.change_boundary_element_s(new_add_nodes_map, max_line_size)
            new_elements[idx] = new_element

    end_time5_1 = datetime.datetime.now()
    print(f"多面体单元替换时间: {(end_time5_1 - end_time5).total_seconds()} 秒")

    # 验证原始节点是否被修改（地址不变，属性更新）
    # target_node = original_nodes_map.get(22393)
    # if target_node:
    #     print(f"切割后原始节点地址: {id(target_node)}, clip={target_node.clip}")

    # 6. 后续步骤（合并节点、重排、输出等）不变
    new_nodes, new_add_node = merge_duplicate_nodes(
        elements=new_elements,
        original_nodes=original_nodes_map,
        max_original_node_id=max_original_node_id,
        precision=8
    )
    end_time6 = datetime.datetime.now()
    print(f"合并节点时间: {(end_time6 - end_time5_1).total_seconds()} 秒")

    new_elements = renumber_element_ids(new_elements)
    end_time7 = datetime.datetime.now()
    print(f"单元重排时间: {(end_time7 - end_time6).total_seconds()} 秒")

    new_add_nodes_map = {node.node_id: node for node in new_add_node}
    if is_handle_boundary==1:
        new_elements = handle_boundary_element(new_elements, new_add_nodes_map, max_line_size)
    else:
        pass
    end_time8 = datetime.datetime.now()
    print(f"处理边界时间: {(end_time8 - end_time7).total_seconds()} 秒")

    write_grid_file_02(output_filename, new_nodes, new_elements)
    end_time9 = datetime.datetime.now()
    print(f"输出文件时间: {(end_time9 - end_time8).total_seconds()} 秒")

    # 打印耗时
    # print(f"读取控制文件时间: {(end_time1 - start_time).total_seconds()} 秒")
    # print(f"读取节点单元时间: {(end_time2 - end_time1).total_seconds()} 秒")
    # print(f"最大单元号时间: {(end_time3 - end_time2).total_seconds()} 秒")
    # print(f"多线程切割时间: {(end_time4 - end_time3).total_seconds()} 秒")
    # print(f"收集结果时间: {(end_time5 - end_time4).total_seconds()} 秒")
    # print(f"合并节点时间: {(end_time6 - end_time5).total_seconds()} 秒")
    # print(f"单元重排时间: {(end_time7 - end_time6).total_seconds()} 秒")
    # print(f"处理边界时间: {(end_time8 - end_time7).total_seconds()} 秒")
    # print(f"输出文件时间: {(end_time9 - end_time8).total_seconds()} 秒")
##########################
#######检索最近的单元和节点
##########################
def search_latest_ele(filename="control.txt",gridname="Inimesh.dat"):
    class ele_pair():
        def __init__(self,id_coor):
            self.label=id_coor[0]
            self.id=id_coor[1]
            self.coor = id_coor[2:5]
            self.ele_id =None
            self.ele_coor = None
            self.materials = id_coor[5:]
            print(self.materials)
            self.material = None

            # 读取控制文件
    cleaned_lines = read_and_clean_file(filename)

    ele_numbers = list(map(int, cleaned_lines.pop(0).split()))

    id_coor = []

    for i in range(ele_numbers[0]):
        # 读取范围信息，跳过第一列字符串
        line_data = cleaned_lines.pop(0).split()
        id_coor.append([line_data[0]] + list(map(float, line_data[1:])))
    print(id_coor)
    # 读取网格文件
    _, elements, _, _ = read_grid_file(gridname)
    # 检索最近的单元
    measured_points = [ele_pair(coor) for coor in id_coor]

    def find_nearest_element(ele_pair):
        min_distance = float('inf')
        nearest_element = None
        for element in elements:
            if element.m_id in ele_pair.materials:
                center = element.center
                distance = np.linalg.norm(np.array(ele_pair.coor) - center)
                if distance < min_distance:
                    min_distance = distance
                    nearest_element = element
        return nearest_element

    # 使用线程池并行处理
    with ThreadPoolExecutor() as executor:
        nearest_elements = list(executor.map(find_nearest_element, measured_points))



    for i, ele in enumerate(nearest_elements):
        print(ele.e_id)
        measured_points[i].ele_id = ele.e_id
        measured_points[i].ele_coor = ele.center
        measured_points[i].material = ele.m_id
        # 准备数据输出到 Excel
    data = []
    for point in measured_points:
        data.append([
            point.label, point.id, point.ele_id,
            point.coor[0], point.coor[1], point.coor[2],
            point.ele_coor[0], point.ele_coor[1], point.ele_coor[2],point.material
        ])

    df = pd.DataFrame(
        data,
        columns=['测点label', '测点id', '单元id', '测点坐标x', '测点坐标y', '测点坐标z',
                 '单元的形心点坐标x', '单元的形心点坐标y', '单元的形心点坐标z', '单元的材料号']
    )
    df.to_excel('output_elements.xlsx', index=False)



def search_latest_node(filename="control.txt", gridname="Inimesh.dat"):
    class point_info:
        def __init__(self, id_coor):
            self.label = id_coor[0]
            self.id = id_coor[1]
            self.coor = id_coor[2:5]
            self.node_id = None
            self.node_coor = None

    # 读取控制文件
    cleaned_lines = read_and_clean_file(filename)

    # 获取要处理的点数量
    point_numbers = list(map(int, cleaned_lines.pop(0).split()))

    id_coor = []

    for i in range(point_numbers[0]):
        # 读取范围信息，跳过第一列字符串
        line_data = cleaned_lines.pop(0).split()
        id_coor.append([line_data[0]] + list(map(float, line_data[1:])))


    # 读取节点文件
    nodes, _, _, _ = read_grid_file(gridname)

    # 检索最近的节点
    measured_points = [point_info(coor) for coor in id_coor]

    def find_nearest_node(point_info):
        min_distance = float('inf')
        nearest_node = None
        for node in nodes:
            node_coor = np.array([node.x, node.y, node.z])
            distance = np.linalg.norm(np.array(point_info.coor) - node_coor)
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        return nearest_node

    # 使用线程池并行处理
    with ThreadPoolExecutor() as executor:
        nearest_nodes = list(executor.map(find_nearest_node, measured_points))

    for i, node in enumerate(nearest_nodes):
        measured_points[i].node_id = node.node_id
        measured_points[i].node_coor = [node.x, node.y, node.z]

    # 准备数据输出到 Excel
    data = []
    for point in measured_points:
        data.append([
            point.label, point.id, point.node_id,
            point.coor[0], point.coor[1], point.coor[2],
            point.node_coor[0], point.node_coor[1], point.node_coor[2]
        ])

    df = pd.DataFrame(
        data,
        columns=['测点label', '测点id', '节点id', '测点坐标x', '测点坐标y', '测点坐标z',
                 '节点坐标x', '节点坐标y', '节点坐标z']
    )
    df.to_excel('output_nodes.xlsx', index=False)


#
###################################################################################################
###########################################单元类型转换###############################################
###################################################################################################

# ------------------------------------------------------------------------------
# 2. 单元转换核心类（仅负责“怎么转”，不绑定固定条件）
# ------------------------------------------------------------------------------
class ElementConverter:
    def __init__(self):
        # 转换方法库：key=(旧类型, 新类型)，value=转换逻辑函数
        self.conversion_methods: Dict[tuple, Callable[[Element, int], Element]] = {}
        self._init_default_conversion_methods()  # 初始化默认转换方法

    def _init_default_conversion_methods(self):
        """初始化常用的单元转换方法（可根据业务扩展）"""
        # 同结构转换（仅改类型，节点/属性不变）：覆盖6→500、9→903等
        same_struct_rules = [
            (60, 601), (60, 602),
            (57, 59), (57, 80),
            (6, 5), (6, 500),
            (1, 2), (1, 222),
            (4, 700), (4, 777),
            (44, 47), (44, 470),
            (9, 902), (9, 903)  # 关键：9→903已注册
        ]
        for old, new in same_struct_rules:
            self.register_conversion_method(old, new, self._convert_same_structure)

        # 特殊转换（需额外逻辑）
        self.register_conversion_method(6, 61, self._convert_6_to_61)  # 示例特殊规则

    def register_conversion_method(self,
                                   old_type: int,
                                   new_type: int,
                                   conversion_method: Callable[[Element, int], Element]):
        """
        注册新的单元转换方法（对外扩展接口）

        参数:
            old_type: 待转换的旧单元类型
            new_type: 目标新单元类型
            conversion_method: 转换逻辑函数（输入旧单元+新类型，输出新单元）
        """
        if not callable(conversion_method):
            raise TypeError("conversion_method必须是可调用函数（如def定义的函数）")
        self.conversion_methods[(old_type, new_type)] = conversion_method
        print(f"已注册转换方法：{old_type}→{new_type}")

    def execute_conversion(self,
                           element: Element,
                           old_type: int,
                           new_type: int) -> Element:
        """
        执行单元转换（前提：已确认单元满足转换条件）

        参数:
            element: 待转换的单元
            old_type: 旧单元类型（用于校验和匹配转换方法）
            new_type: 目标新单元类型

        返回:
            转换后的单元（失败则返回原单元）
        """
        # 1. 基础校验：单元类型是否匹配旧类型
        if element.t_id != old_type:
            print(f"⚠️  单元{element.e_id}：当前类型{element.t_id}≠指定旧类型{old_type}，跳过转换")
            return element

        # 2. 校验转换方法是否存在
        method_key = (old_type, new_type)
        if method_key not in self.conversion_methods:
            raise ValueError(
                f"❌ 未找到{old_type}→{new_type}的转换方法！\n"
                f"请先调用 register_conversion_method({old_type}, {new_type}, 转换函数) 注册"
            )

        # 3. 执行转换逻辑
        try:
            conversion_func = self.conversion_methods[method_key]
            new_element = conversion_func(element, new_type)
            print(f"✅ 单元{element.e_id}：{old_type}→{new_type}转换成功")
            return new_element
        except Exception as e:
            print(f"❌ 单元{element.e_id}转换失败：{str(e)}，保留原类型")
            return element

    # ------------------------------
    # 具体转换逻辑（根据单元类型定义）
    # ------------------------------

    def _convert_same_structure(self, old_element: Element, new_type: int) -> Element:

        old_element.t_id = new_type

        # 创建新单元（继承原单元ID、材料ID，更新类型和节点）
        return old_element

    def _convert_6_to_61(self, old_element: Element, new_type: int) -> Element:
        if old_element.points[3].node_id == old_element.points[4].node_id and old_element.points[4].node_id == \
                old_element.points[5].node_id and old_element.points[5].node_id == old_element.points[6].node_id and \
                old_element.points[6].node_id == old_element.points[7].node_id:
            old_element.t_id = new_type
            return old_element

    # def _convert_60_to_9(self, old_element: Element, new_type: int) -> Element:
    #     """
    #     60号单元 → 9号单元 转换逻辑（示例：9号单元仅保留前6个节点）
    #     注：实际逻辑需与您的单元定义对齐（如节点顺序、属性继承等）
    #     """
    #     # 校验60号单元的节点数（假设60号单元必须≥6个节点才能转9号）
    #     if old_element.num_point < 6:
    #         raise ValueError(f"60号单元需≥6个节点（当前{old_element.num_point}个），无法转9号单元")
    #
    #     # 9号单元取前6个节点（按实际单元定义调整）
    #     new_points = old_element.points[:6]
    #
    #     # 创建新单元（继承原单元ID、材料ID，更新类型和节点）
    #     return ElementFactory.create_element(
    #         e_id=old_element.e_id,
    #         t_id=new_type,
    #         m_id=old_element.m_id,
    #         points=new_points
    #     )


# ------------------------------------------------------------------------------
# 3. 外部条件判断工具（独立于转换类，支持灵活定义条件）
# ------------------------------------------------------------------------------
def check_element_conversion_condition(element: Element,
                                       old_type: int,
                                       condition_input: Union[bool, List[Callable[[Element], bool]], Dict]) -> bool:
    """
    检查单元是否满足转换条件（支持3种灵活输入方式）

    参数:
        element: 待检查的单元
        old_type: 目标旧单元类型（先校验单元类型）
        condition_input: 条件输入（3种类型可选）
            - bool：直接指定是否满足（如用户手动选择）
            - List[Callable]：条件函数列表（默认and逻辑）
            - Dict：带逻辑的条件配置（如{"conditions": [...], "logic": "or"}）

    返回:
        bool：是否满足转换条件
    """
    # 前置校验：单元类型是否匹配
    if element.t_id != old_type:
        return False

    # 处理不同类型的条件输入
    if isinstance(condition_input, bool):
        # 方式1：外部直接指定结果（如用户勾选“允许转换”）
        return condition_input

    elif isinstance(condition_input, list) and all(callable(cond) for cond in condition_input):
        # 方式2：条件函数列表（默认所有条件都满足）
        return all(cond(element) for cond in condition_input)

    elif isinstance(condition_input, dict):
        # 方式3：带逻辑的条件配置（支持and/or）
        required_keys = ["conditions"]
        if not all(key in condition_input for key in required_keys):
            raise ValueError("条件字典必须包含'conditions'键（值为条件函数列表）")

        conditions = condition_input["conditions"]
        logic = condition_input.get("logic", "and")  # 默认and逻辑

        # 校验条件格式
        if not isinstance(conditions, list) or not all(callable(cond) for cond in conditions):
            raise ValueError("'conditions'必须是可调用函数的列表（如lambda或def定义的函数）")
        if logic not in ["and", "or"]:
            raise ValueError(f"逻辑类型仅支持'and'/'or'，当前为{logic}")

        # 执行条件判断
        if logic == "and":
            return all(cond(element) for cond in conditions)
        else:
            return any(cond(element) for cond in conditions)

    else:
        raise TypeError(
            "condition_input仅支持3种类型：\n"
            "1. bool（直接指定是否满足）\n"
            "2. List[Callable]（条件函数列表，默认and逻辑）\n"
            "3. Dict（如{'conditions': [...], 'logic': 'or'}）"
        )


# ------------------------------------------------------------------------------
# 4. 对外统一接口（先判断条件，满足后再执行转换）
# ------------------------------------------------------------------------------
def convert_element_with_condition(element: Element,
                                   old_type: int,
                                   new_type: int,
                                   condition_input: Union[bool, List[Callable[[Element], bool]], Dict],
                                   converter: Optional[ElementConverter] = None) -> Element:
    """
    单个单元转换接口：先判断条件，满足后执行转换

    参数:
        element: 待转换单元
        old_type: 旧单元类型
        new_type: 新单元类型
        condition_input: 转换条件（3种输入方式）
        converter: 转换实例（可选，默认自动创建）

    返回:
        Element：转换后/原单元
    """
    # 初始化转换器（默认实例，也可外部传入自定义实例）
    if converter is None:
        converter = ElementConverter()

    # 步骤1：检查是否满足转换条件
    if not check_element_conversion_condition(element, old_type, condition_input):
        print(f"⚠️  单元{element.e_id}：不满足转换条件，保留原类型")
        return element

    # 步骤2：满足条件，执行转换
    return converter.execute_conversion(element, old_type, new_type)


def batch_convert_elements(elements: List[Element],
                           old_type: int,
                           new_type: int,
                           condition_input: Union[bool, List[Callable[[Element], bool]], Dict],
                           converter: Optional[ElementConverter] = None) -> List[Element]:
    """
    批量单元转换接口：对每个单元执行“条件判断→转换”流程

    参数:
        elements: 待转换单元列表
        old_type: 旧单元类型
        new_type: 新单元类型
        condition_input: 转换条件（3种输入方式）
        converter: 转换实例（可选）

    返回:
        List[Element]：转换后的单元列表
    """
    if not isinstance(elements, list):
        raise TypeError("elements必须是Element实例的列表")

    # 批量处理每个单元
    return [
        convert_element_with_condition(elem, old_type, new_type, condition_input, converter)
        for elem in elements
    ]

def change_eleId_by_mat(controlFilename,inimeshFilename,OutInimeshFilename):

    """
    批量单元转换接口：对每个单元执行“条件判断→转换”流程

    参数:
        elements: 待转换单元列表
        old_type: 旧单元类型
        new_type: 新单元类型
        condition_input: 转换条件（3种输入方式）
        converter: 转换实例（可选）

    返回:
        List[Element]：转换后的单元列表
    """
    start_time = time.time()

    # 1. 先读取所有节点（节点数量通常小于单元，可一次性加载）
    nodes, elements, _, _ = read_grid_file(inimeshFilename)
    total_nodes = len(nodes)
    total_elements = len(elements)
    print(f"总节点数: {total_nodes:,}，总单元数: {total_elements:,}")

    # 6. 读取材料对信息，判断节点是否在材料对上
    class ele_pair:
        def __init__(self, oldId1, oldId2):
            """
            初始化材料对对象

            参数:
                mat1: 第一种材料的标识（将被转换为整数）
                mat2: 第二种材料的标识（将被转换为整数）
            """
            try:
                # 将输入转换为整数（处理从文件读取的字符串数据）
                self.oldId1 = int(oldId1)
                self.oldId2 = int(oldId2)
            except ValueError as e:
                # 提供更明确的错误信息，便于调试
                raise ValueError(f"材料号必须为整数，无法转换: mat1={oldId1}, mat2={oldId2}") from e

            # 可选：添加材料号有效性验证（根据实际业务需求调整）
            if self.oldId1 < 0 or self.oldId2 < 0:
                raise ValueError(f"材料号不能为负数: mat1={self.oldId1}, mat2={self.oldId2}")


    convert = ElementConverter()
    cleaned_lines = read_and_clean_file(controlFilename)
    mat_pairs_numbers = 0
    mats = []
    ele_type_pairs_numbers = 0
    ele_pairs = []


    if cleaned_lines:
        # 读取材料对数量

        mat_pairs_numbers = list(map(int, cleaned_lines.pop(0).split()))[0]
        mats = []


        for i in range(mat_pairs_numbers):
            if not cleaned_lines:
                raise IndexError(f"文件内容不足，无法读取第{i + 1}个材料")
            line_data = cleaned_lines.pop(0).split()
            if len(line_data) != 1:
                raise ValueError(f"材料对数据格式错误，行应为1个整数: {line_data}")

            # 使用改进后的mat_pair类
            mats.append(int(line_data[0]))


        ele_type_pairs_numbers = list(map(int, cleaned_lines.pop(0).split()))[0]
        ele_pairs = []

        for i in range(ele_type_pairs_numbers):
            if not cleaned_lines:
                raise IndexError(f"文件内容不足，无法读取第{i + 1}个材料对")
            line_data = cleaned_lines.pop(0).split()
            if len(line_data) != 2:
                raise ValueError(f"材料对数据格式错误，第应为两个整数: {line_data}")

            # 使用改进后的mat_pair类
            ele_pairs.append(ele_pair(*line_data))

        # 验证结果
        for i, pair in enumerate(ele_pairs):
            print(f"材料对 {i + 1}: type1={pair.oldId1}, type2={pair.oldId2}")

        for i in range(len(elements)):
            if elements[i].m_id in mats:
                for ele_pair_n in ele_pairs:
                    if elements[i].t_id == ele_pair_n.oldId1:
                        elements[i] = convert_element_with_condition(elements[i], ele_pair_n.oldId1, ele_pair_n.oldId2, True, convert)

        write_grid_file_02(OutInimeshFilename, nodes, elements)

# ------------------------------------------------------------------------------
# 5. 完整测试示例（覆盖3种条件输入方式+批量转换以作参考）
# ------------------------------------------------------------------------------
def full_demo():
    """完整演示：创建测试数据→3种条件转换→输出结果"""
    print("=" * 80)
    print("1. 准备测试数据（节点+单元）")
    print("=" * 80)

    #  创建8个测试节点（坐标模拟实际场景）
    test_nodes = [
        Node(node_id=1, x=0.0, y=0.0, z=0.0),
        Node(node_id=2, x=1.0, y=0.0, z=0.0),
        Node(node_id=3, x=1.0, y=1.0, z=0.0),
        Node(node_id=4, x=0.0, y=1.0, z=0.0),
        Node(node_id=5, x=0.0, y=0.0, z=1.0),
        Node(node_id=6, x=1.0, y=0.0, z=1.0),
        Node(node_id=7, x=1.0, y=1.0, z=1.0),
        Node(node_id=8, x=1.0, y=1.0, z=1.0)  # 与节点7坐标重合
    ]

    # 创建3个测试单元（2个60号，1个9号）
    test_elements = [
        # 单元1：60号（满足转换条件：8节点、材料1、最后两节点重合）
        ElementFactory.create_element(
            e_id=101, t_id=60, m_id=1, points=test_nodes
        ),
        # 单元2：60号（不满足条件：7节点、材料2）
        ElementFactory.create_element(
            e_id=102, t_id=60, m_id=2, points=test_nodes[:7]
        ),
        # 单元3：9号（满足转换条件：6节点、材料1）
        ElementFactory.create_element(
            e_id=103, t_id=9, m_id=1, points=test_nodes[:6]
        )
    ]

    # 打印初始数据
    for elem in test_elements:
        print(f"初始单元：{elem}")

    # ------------------------------
    # 场景1：直接传bool条件（外部已判断，强制转换）
    # ------------------------------
    print("\n" + "=" * 80)
    print("2. 场景1：直接传bool条件（True=允许转换所有60→9）")
    print("=" * 80)
    # 复制测试数据（避免影响其他场景）
    elements_scene1 = [elem for elem in test_elements if elem.t_id == 60]
    # 批量转换：60→9，条件直接传True（所有60号单元都转）
    result_scene1 = batch_convert_elements(
        elements=elements_scene1,
        old_type=60,
        new_type=9,
        condition_input=True  # 外部强制允许转换
    )
    # 输出结果
    for elem in result_scene1:
        print(f"场景1结果：{elem}")

    # ------------------------------
    # 场景2：传条件函数列表（and逻辑，需所有条件满足）
    # ------------------------------
    print("\n" + "=" * 80)
    print("3. 场景2：条件函数列表（and逻辑：60→9需满足3个条件）")
    print("=" * 80)

    # 定义3个条件函数（60→9的严格条件）
    def cond_node_count(elem):
        """条件1：节点数=8"""
        return elem.num_point == 8

    def cond_material_id(elem):
        """条件2：材料ID=1"""
        return elem.m_id == 1

    def cond_last_two_nodes_coincide(elem):
        """条件3：最后两个节点坐标完全重合（精度1e-6）"""
        node7 = elem.points[-2]
        node8 = elem.points[-1]

        return (abs(node7.x - node8.x) < 1e-6 and
                abs(node7.y - node8.y) < 1e-6 and
                abs(node7.z - node8.z) < 1e-6)

    # 条件列表（and逻辑：所有条件必须满足）
    condition_list = [cond_node_count, cond_material_id, cond_last_two_nodes_coincide]

    # 批量转换60→9
    elements_scene2 = [elem for elem in test_elements if elem.t_id == 60]
    result_scene2 = batch_convert_elements(
        elements=elements_scene2,
        old_type=60,
        new_type=9,
        condition_input=condition_list
    )
    # 输出结果
    for elem in result_scene2:
        print(f"场景2结果：{elem}")

    # ------------------------------
    # 场景3：传带or逻辑的条件配置（满足任一条件即可）
    # ------------------------------
    print("\n" + "=" * 80)
    print("4. 场景3：带or逻辑的条件配置（9→60需满足任一条件）")
    print("=" * 80)
    # 条件配置：or逻辑（满足任一即可）
    condition_config = {
        "conditions": [
            lambda elem: elem.m_id == 1,  # 条件1：材料ID=1
            lambda elem: elem.num_point == 6  # 条件2：节点数=6
        ],
        "logic": "or"  # 满足任一条件即可转换
    }

    # 批量转换9→60
    elements_scene3 = [elem for elem in test_elements if elem.t_id == 9]
    result_scene3 = batch_convert_elements(
        elements=elements_scene3,
        old_type=9,
        new_type=60,
        condition_input=condition_config
    )
    # 输出结果
    for elem in result_scene3:
        print(f"场景3结果：{elem}")

# ------------------------------------------------------------------------------
# 5. 根据材料改为交叉迭代或者改为直接迭代
# ------------------------------------------------------------------------------








######################################################################################################################
###########################################添加孔压约束-根据不同材料的共节点区###############################################
######################################################################################################################
# --------------------------
# 1. 数据结构与基础函数优化
# --------------------------
# def process_batch(batch_elements, node_id_material):
#     """处理一批单元，更新节点-材料映射（供多进程使用）"""
#     for element in batch_elements:
#         material_id = element.m_id
#         # 遍历单元节点，更新材料集合（用set避免重复）
#         for node in element.points:
#             node_id = node.node_id
#             if node_id in node_id_material:
#                 node_id_material[node_id].add(material_id)
#             else:
#                 node_id_material[node_id] = {material_id}
#     return node_id_material
#
#
# # --------------------------
# # 2. 主处理函数（分批次+多进程）
# # --------------------------
# def add_materials_large_scale(controlfilename="control.dat",Inimeshfilename="Inimesh.dat",outfilename="out_Inimesh.dat", batch_size=10000):
#     """
#     处理超大量单元和节点的场景：
#     - 分批次读取单元，避免一次性加载全部数据
#     - 多进程并行处理批次，利用多核CPU
#     - 用set和dict优化存储与查找
#     """
#     start_time = time.time()
#
#     # 1. 先读取所有节点（节点数量通常小于单元，可一次性加载）
#     nodes, elements, node_map, _ = read_grid_file(Inimeshfilename)
#     total_nodes = len(nodes)
#     total_elements = len(elements)
#     print(f"总节点数: {total_nodes:,}，总单元数: {total_elements:,}")
#
#     # 2. 初始化节点ID到材料集合的映射（用dict+set，高效去重与查找）
#     # 键：node_id，值：材料号集合（set）
#     node_id_material = {}
#
#     # 3. 分批次处理单元（核心优化：避免一次性加载所有单元到内存）
#     # 计算批次数
#     num_batches = (total_elements + batch_size - 1) // batch_size
#     print(f"分批次处理：{num_batches} 批（每批 {batch_size} 个单元）")
#
#     # 4. 多进程并行处理批次（根据CPU核心数设置进程数）
#     num_processes = min(cpu_count(), num_batches)  # 进程数不超过CPU核心数
#     pool = Pool(processes=num_processes)
#
#     # 拆分单元为批次
#     batches = [elements[i:i + batch_size] for i in range(0, total_elements, batch_size)]
#
#     # 并行处理所有批次（partial固定node_id_material参数）
#     results = pool.map(partial(process_batch, node_id_material=node_id_material), batches)
#
#     # 合并多进程结果（不同进程可能处理同一节点，需合并材料号）
#     final_material_map = {}
#     for result in results:
#         for node_id, materials in result.items():
#             if node_id in final_material_map:
#                 final_material_map[node_id].update(materials)
#             else:
#                 final_material_map[node_id] = materials
#
#     pool.close()
#     pool.join()
#
#     # 5. 将材料号集合转换为列表，添加到节点对象（紧凑存储）
#     # 用numpy数组存储材料号（比list更节省内存，尤其大量数据时）
#     for node in nodes:
#         materials = final_material_map.get(node.node_id, set())
#         # 转换为sorted numpy数组（int32类型，减少内存）
#         node.materials = np.array(sorted(materials), dtype=np.int32)
#
#
#     # 6. 读取材料对信息，判断节点是否在材料对上
#     # 用numpy数组存储材料号（比list更节省内存，尤其大量数据时）
#     class mat_pair:
#         def __init__(self, mat1, mat2):
#             """
#             初始化材料对对象
#
#             参数:
#                 mat1: 第一种材料的标识（将被转换为整数）
#                 mat2: 第二种材料的标识（将被转换为整数）
#             """
#             try:
#                 # 将输入转换为整数（处理从文件读取的字符串数据）
#                 self.mat1 = int(mat1)
#                 self.mat2 = int(mat2)
#             except ValueError as e:
#                 # 提供更明确的错误信息，便于调试
#                 raise ValueError(f"材料号必须为整数，无法转换: mat1={mat1}, mat2={mat2}") from e
#
#             # 可选：添加材料号有效性验证（根据实际业务需求调整）
#             if self.mat1 < 0 or self.mat2 < 0:
#                 raise ValueError(f"材料号不能为负数: mat1={self.mat1}, mat2={self.mat2}")
#
#
#     cleaned_lines = read_and_clean_file(controlfilename)
#
#     if cleaned_lines:
#         # 读取材料对数量
#         mat_pairs_numbers = list(map(int, cleaned_lines.pop(0).split()))[0]
#         mat_pairs = []
#
#         for i in range(mat_pairs_numbers):
#             if not cleaned_lines:
#                 raise IndexError(f"文件内容不足，无法读取第{i + 1}个材料对")
#             line_data = cleaned_lines.pop(0).split()
#             if len(line_data) != 2:
#                 raise ValueError(f"材料对数据格式错误，第{i + 1}行应为两个整数: {line_data}")
#
#             # 使用改进后的mat_pair类
#             mat_pairs.append(mat_pair(*line_data))
#
#         # 验证结果
#         for i, pair in enumerate(mat_pairs):
#             print(f"材料对 {i + 1}: mat1={pair.mat1}, mat2={pair.mat2}")
#
#         for node in nodes:
#             for mat_pairn in mat_pairs:
#                 if mat_pairn.mat1 in node.materials and mat_pairn.mat2 in node.materials:
#                     node.press=1
#
#     write_grid_file_02(outfilename, nodes, elements)
#
#     end_time = time.time()
#     print(f"处理完成，总耗时: {end_time - start_time:.4f} 秒")

def process_batch(batch_elements):
    """处理一批单元，返回该批次的节点-材料映射（供多进程使用）"""
    # 每个进程使用独立的字典，避免多进程数据冲突
    batch_result = {}
    for element in batch_elements:
        material_id = element.m_id
        # 遍历单元节点，更新材料集合（用set避免重复）
        for node in element.points:
            node_id = node.node_id
            if node_id in batch_result:
                batch_result[node_id].add(material_id)
            else:
                batch_result[node_id] = {material_id}
    return batch_result


# --------------------------
# 2. 主处理函数（分批次+多进程）
# --------------------------
def add_materials_large_scale(controlfilename="control.dat", Inimeshfilename="Inimesh.dat",
                             outfilename="out_Inimesh.dat", batch_size=10000):
    """
    处理超大量单元和节点的场景：
    - 分批次读取单元，避免一次性加载全部数据
    - 多进程并行处理批次，利用多核CPU
    - 用set和dict优化存储与查找
    """
    start_time = time.time()

    # 1. 先读取所有节点（节点数量通常小于单元，可一次性加载）
    nodes, elements, node_map, _ = read_grid_file(Inimeshfilename)
    total_nodes = len(nodes)
    total_elements = len(elements)
    print(f"总节点数: {total_nodes:,}，总单元数: {total_elements:,}")

    # 3. 分批次处理单元（核心优化：避免一次性加载所有单元到内存）
    # 计算批次数
    num_batches = (total_elements + batch_size - 1) // batch_size
    print(f"分批次处理：{num_batches} 批（每批 {batch_size} 个单元）")

    # 4. 多进程并行处理批次（根据CPU核心数设置进程数）
    num_processes = min(cpu_count(), num_batches)  # 进程数不超过CPU核心数
    print(f"使用 {num_processes} 个进程并行处理")

    # 拆分单元为批次
    batches = [elements[i:i + batch_size] for i in range(0, total_elements, batch_size)]

    # 使用上下文管理器创建进程池，自动管理资源
    with Pool(processes=num_processes) as pool:
        # 并行处理所有批次
        results = pool.map(process_batch, batches)

    # 合并多进程结果（不同进程可能处理同一节点，需合并材料号）
    final_material_map = {}
    for result in results:
        for node_id, materials in result.items():
            if node_id in final_material_map:
                final_material_map[node_id].update(materials)
            else:
                final_material_map[node_id] = materials

    # 5. 将材料号集合转换为列表，添加到节点对象（紧凑存储）
    # 用numpy数组存储材料号（比list更节省内存，尤其大量数据时）
    for node in nodes:
        materials = final_material_map.get(node.node_id, set())
        # 转换为sorted numpy数组（int32类型，减少内存）
        node.materials = np.array(sorted(materials), dtype=np.int32)


    # 6. 读取材料对信息，判断节点是否在材料对上
    class mat_pair:
        def __init__(self, mat1, mat2):
            """
            初始化材料对对象

            参数:
                mat1: 第一种材料的标识（将被转换为整数）
                mat2: 第二种材料的标识（将被转换为整数）
            """
            try:
                # 将输入转换为整数（处理从文件读取的字符串数据）
                self.mat1 = int(mat1)
                self.mat2 = int(mat2)
            except ValueError as e:
                # 提供更明确的错误信息，便于调试
                raise ValueError(f"材料号必须为整数，无法转换: mat1={mat1}, mat2={mat2}") from e

            # 可选：添加材料号有效性验证（根据实际业务需求调整）
            if self.mat1 < 0 or self.mat2 < 0:
                raise ValueError(f"材料号不能为负数: mat1={self.mat1}, mat2={self.mat2}")


    cleaned_lines = read_and_clean_file(controlfilename)

    if cleaned_lines:
        # 读取材料对数量
        mat_pairs_numbers = list(map(int, cleaned_lines.pop(0).split()))[0]
        mat_pairs = []

        for i in range(mat_pairs_numbers):
            if not cleaned_lines:
                raise IndexError(f"文件内容不足，无法读取第{i + 1}个材料对")
            line_data = cleaned_lines.pop(0).split()
            if len(line_data) != 2:
                raise ValueError(f"材料对数据格式错误，第{i + 1}行应为两个整数: {line_data}")

            # 使用改进后的mat_pair类
            mat_pairs.append(mat_pair(*line_data))

        # 验证结果
        for i, pair in enumerate(mat_pairs):
            print(f"材料对 {i + 1}: mat1={pair.mat1}, mat2={pair.mat2}")

        for node in nodes:
            for mat_pairn in mat_pairs:
                if mat_pairn.mat1 in node.materials and mat_pairn.mat2 in node.materials:
                    node.press = 1

    write_grid_file_02(outfilename, nodes, elements)

    end_time = time.time()
    print(f"处理完成，总耗时: {end_time - start_time:.4f} 秒")



######################################################################################################################
###########################################添加孔压约束-根据不同材料的共节点区###############################################
######################################################################################################################