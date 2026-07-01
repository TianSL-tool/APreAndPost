import numpy as np

from Element.ElementFactory import ElementFactory

# 使用示例
class Face:
    """面的类定义，包含邻居单元信息"""

    def __init__(self, id, nodes, neighbour_cell1, neighbour_cell2=0):
        self.id = id
        self.nodes = nodes  # 节点编号列表
        self.neighbour_cell1 = neighbour_cell1  # 邻居单元1的ID
        self.neighbour_cell2 = neighbour_cell2  # 邻居单元2的ID

    def __repr__(self):
        neighbours = f"n1={self.neighbour_cell1}, n2={self.neighbour_cell2}"
        return f"Face(id={self.id}, nodes={self.nodes}, {neighbours})"

def create_face_list(elements):
    faces = []
    face_id = 0
    for element in elements:
        if element.t_id == 6:# 如果是六面体
            nodes_id = np.zeros(8)
            for i, point in enumerate(element.points):
                nodes_id[i] = point.node_id
            nodes1 = [int(nodes_id[0]), int(nodes_id[3]), int(nodes_id[2]), int(nodes_id[1])]  # 底面
            nodes2 = [int(nodes_id[4]), int(nodes_id[5]), int(nodes_id[6]), int(nodes_id[7])]  # 顶面
            nodes3 = [int(nodes_id[0]), int(nodes_id[4]), int(nodes_id[7]), int(nodes_id[3])]  # 左面
            nodes4 = [int(nodes_id[1]), int(nodes_id[2]), int(nodes_id[6]), int(nodes_id[5])]  # 右面
            nodes5 = [int(nodes_id[0]), int(nodes_id[1]), int(nodes_id[5]), int(nodes_id[4])]  # 前面
            nodes6 = [int(nodes_id[2]), int(nodes_id[3]), int(nodes_id[7]), int(nodes_id[6])]  # 后面
            nodes1 = remove_adjacent_duplicates(nodes1)
            nodes2 = remove_adjacent_duplicates(nodes2)
            nodes3 = remove_adjacent_duplicates(nodes3)
            nodes4 = remove_adjacent_duplicates(nodes4)
            nodes5 = remove_adjacent_duplicates(nodes5)
            nodes6 = remove_adjacent_duplicates(nodes6)
            face_id += 1
            face1 = Face(face_id, nodes1, element.e_id)
            faces.append(face1)
            face_id += 1
            face2 = Face(face_id, nodes2, element.e_id)
            faces.append(face2)
            face_id += 1
            face3 = Face(face_id, nodes3, element.e_id)
            faces.append(face3)
            face_id += 1
            face4 = Face(face_id, nodes4, element.e_id)
            faces.append(face4)
            face_id += 1
            face5 = Face(face_id, nodes5, element.e_id)
            faces.append(face5)
            face_id += 1
            face6 = Face(face_id, nodes6, element.e_id)
            faces.append(face6)

        elif element.t_id == 57:
            for face_index in range(element.mian_num):
                # mianDian中存储的是node对象
                node_objects = element.mianDian[face_index]
                node_ids = [node.node_id for node in node_objects]
                face = Face(
                    id=None,  # face ID稍后统一分配
                    nodes=node_ids,
                    neighbour_cell1=element.e_id,
                    neighbour_cell2=0
                )
                faces.append(face)

    unique_faces, unique_face_map = remove_duplicate_faces_with_neighbours(faces)

    return unique_faces, unique_face_map

def remove_adjacent_duplicates(nums):
    return [n for i, n in enumerate(nums) if i == 0 or n != nums[i - 1]]

def remove_duplicate_faces_with_neighbours(faces):
    """
    去重面并合并邻居单元信息

    规则：
    1. 第一次出现的面：保留neighbour_cell1，neighbour_cell2=0
    2. 重复的面：将其neighbour_cell1赋值给已存在面的neighbour_cell2

    参数:
        faces: 包含face对象的列表

    返回:
        unique_faces: 去重后的faces列表
    """

    face_dict = {}  # key: 标准化节点, value: (face对象, 是否已设置neighbour_cell2)
    unique_faces = []
    unique_face_map = {}

    # 第一次遍历：处理所有面
    for face in faces:
        normalized = normalize_face_nodes(face.nodes)

        if normalized in face_dict:
            # 重复面
            existing_face, has_neighbour2 = face_dict[normalized]

            if not has_neighbour2:
                # 如果原始面还没有neighbour_cell2，使用当前面的neighbour_cell1
                existing_face.neighbour_cell2 = face.neighbour_cell1
                face_dict[normalized] = (existing_face, True)  # 标记已设置
            else:
                # 如果原始面已经有neighbour_cell2了，当前面不处理（或者可以记录日志）
                print(f"警告: 面 {face.id} 是 {existing_face.id} 的重复，但原始面已设置neighbour_cell2")
        else:
            # 第一次出现
            face_dict[normalized] = (face, False)  # 标记尚未设置neighbour_cell2

    # 第二次遍历：收集唯一面并重新编号
    new_id_counter = 1
    for normalized, (face, _) in face_dict.items():
        # 创建新的face对象，保持原邻居信息，重新编号
        new_face = Face(
            id=new_id_counter,
            nodes=face.nodes,
            neighbour_cell1=face.neighbour_cell1,
            neighbour_cell2=face.neighbour_cell2
        )
        unique_faces.append(new_face)
        unique_face_map[normalized] = new_face.id
        new_id_counter += 1

    return unique_faces, unique_face_map

def normalize_face_nodes(nodes):
    """
    优化版本：标准化面节点顺序
    支持正向和反向顺序
    """
    if not nodes:
        return tuple()

    n = len(nodes)
    double_nodes = nodes + nodes

    # 考虑正向和反向两种顺序
    all_representations = []

    # 正向循环
    for i in range(n):
        rep = tuple(double_nodes[i:i + n])
        all_representations.append(rep)

    # 反向循环（面的另一面）
    reversed_nodes = list(reversed(nodes))
    double_reversed = reversed_nodes + reversed_nodes
    for i in range(n):
        rep = tuple(double_reversed[i:i + n])
        all_representations.append(rep)

    # 返回最小表示
    return min(all_representations)

def compare_element57_faces(old_element, new_element, tolerance=1e-6):
    """
    比较两个57号单元的全部面
    找到旧单元被切面和对应的新单元切出后的面
    返回一个字典 旧面的节点id->新面的nodes数列
    """
    face_replace_dict = {}

    # 收集所有面的信息
    old_faces_info = []
    new_faces_info = []

    # 旧单元的面信息
    for face_idx, face_nodes in enumerate(old_element.mianDian):
        centroid = calculate_face_centroid(face_nodes)
        old_faces_info.append({
            'index': face_idx,
            'nodes': face_nodes,
            'centroid': centroid,
            'node_ids': [node.node_id for node in face_nodes],
        })

    # 新单元的面信息
    for face_idx, face_nodes in enumerate(new_element.mianDian):
        centroid = calculate_face_centroid(face_nodes)
        new_faces_info.append({
            'index': face_idx,
            'nodes': face_nodes,
            'centroid': centroid,
            'node_ids': [node.node_id for node in face_nodes],
        })

    # 遍历旧单元的每个面，嵌套遍历新单元的每个面
    for old_idx, old_face in enumerate(old_faces_info):
        for new_idx, new_face in enumerate(new_faces_info):
            # 如果两个面共面但是面心不一致，判断这是被切前后的一对面
            if are_faces_coplanar(old_face['nodes'], new_face['nodes'], tolerance):
                if not np.array_equal(old_face['centroid'], new_face['centroid']):
                    normalized_old_face_nodes = normalize_face_nodes(old_face['node_ids'])     # 把旧的面归一化
                    face_replace_dict[normalized_old_face_nodes] = new_face['nodes']        # 给字典里加key和value

    return face_replace_dict

def are_faces_coplanar(face1_nodes, face2_nodes, tolerance=1e-6):
    """
    判断两个面是否在同一平面
    """
    # 获取所有点的坐标
    points1 = [np.array([node.x, node.y, node.z]) for node in face1_nodes]
    points2 = [np.array([node.x, node.y, node.z]) for node in face2_nodes]

    all_points = points1 + points2

    # 如果总点数小于4，总是共面
    if len(all_points) < 4:
        return True

    # 使用前3个点计算平面
    normal, d = calculate_plane_from_points(all_points[:3])

    # 检查所有点是否在平面上
    for point in all_points[3:]:
        distance = point_to_plane_distance(point, normal, d)
        if distance > tolerance:
            return False

    return True

def point_to_plane_distance(point, normal, d):
    """计算点到平面的距离"""
    return abs(np.dot(normal, point) + d)

def calculate_face_centroid(face_nodes):
    """计算面的质心"""
    points = [np.array([node.x, node.y, node.z]) for node in face_nodes]
    centroid = np.mean(points, axis=0)
    return centroid

def calculate_plane_from_points(points):
    """
    从3个或更多点计算平面方程 ax + by + cz + d = 0
    返回: (normal_vector, d)
    """
    if len(points) < 3:
        raise ValueError("至少需要3个点来确定平面")

    # 转换为numpy数组
    points_array = np.array(points)

    # 使用PCA计算法向量
    if len(points) == 3:
        # 三个点直接计算
        v1 = points_array[1] - points_array[0]
        v2 = points_array[2] - points_array[0]
        normal = np.cross(v1, v2)
    else:
        # 多个点使用PCA
        centroid = np.mean(points_array, axis=0)
        centered = points_array - centroid
        _, _, vh = np.linalg.svd(centered)
        normal = vh[2]  # 最小奇异值对应的向量

    # 归一化法向量
    normal_norm = np.linalg.norm(normal)
    if normal_norm > 1e-10:
        normal = normal / normal_norm

    # 计算d
    d = -np.dot(normal, points_array[0])

    return normal, d


def merge_face_replace_dict(face_replace_dict1, face_replace_dict2, element_id):
    """
    比较两个face_replace_dict字典
    face_replace_dict字典示例：{(1, 2, 3, 4): [12, 11, 10, 9], (5, 6, 7, 8): [13, 14, 15, 16], (3, 4, 8, 7): [12, 16, 15, 11], (1, 2, 6, 5): [10, 14, 13, 9]}
    key是旧的面节点编号old_face_nodes，value是新的面节点编号new_face_nodes
    把两个字典key值相同的value创建下面的子字典
    sub_dict{
      'element_id' = element_id
      'new_face_nodes1' = new_face_nodes1
      'new_face_nodes2' = new_face_nodes2
    }
    然后把子字典放入merged_face_replace_dict
    merged_face_replace_dict['old_face_nodes'] = sub_dict
    """
    merged_face_replace_dict = {}

    # 找出两个字典中都有的key（相同的旧面）
    common_keys = set(face_replace_dict1.keys()) & set(face_replace_dict2.keys())

    for old_face_nodes in common_keys:
        # 获取两个字典中对应的新面节点
        new_face_nodes1 = face_replace_dict1[old_face_nodes]
        new_face_nodes2 = face_replace_dict2[old_face_nodes]

        # 创建子字典
        sub_dict = {
            'element_id': element_id,
            'new_face_nodes1': new_face_nodes1,
            'new_face_nodes2': new_face_nodes2,
        }

        # 将子字典放入结果字典
        merged_face_replace_dict[old_face_nodes] = sub_dict

    return merged_face_replace_dict


def convert_merged_dict_to_subdict_list(merged_dict):
    """
    将 merged_dict 中的所有 sub_dict 提取到列表

    merged_dict 格式:
    {
        old_face_nodes1: {
            'element_id': 101,
            'new_face_nodes1': [...],
            'new_face_nodes2': [...]
        },
        old_face_nodes2: {
            'element_id': 102,
            'new_face_nodes1': [...],
            'new_face_nodes2': [...]
        }
    }

    返回:
    [
        {'element_id': 101, 'new_face_nodes1': [...], 'new_face_nodes2': [...], 'old_face_nodes': (1,2,3,4)},
        {'element_id': 102, 'new_face_nodes1': [...], 'new_face_nodes2': [...], 'old_face_nodes': (5,6,7,8)},
        ...
    ]
    """
    subdict_list = []

    for old_face_nodes, sub_dict in merged_dict.items():
        # 创建新的 sub_dict，包含 old_face_nodes
        new_sub_dict = sub_dict.copy()  # 复制原始 sub_dict

        # 添加 old_face_nodes 到 sub_dict
        # 注意：old_face_nodes 可能已经是元组或需要转换
        if isinstance(old_face_nodes, tuple):
            new_sub_dict['old_face_nodes'] = old_face_nodes
        else:
            new_sub_dict['old_face_nodes'] = tuple(old_face_nodes)

        subdict_list.append(new_sub_dict)

    return subdict_list

# def merge_dicts_with_duplicate_removal(dict_list):
#     """
#     合并多个字典，如果key重复，删除所有包含该key的字典
#
#     Args:
#         dict_list: merged_face_replace_dict 字典列表
#
#     Returns:
#         合并后的字典（不包含任何重复key）
#     """
#     # 第一步：统计每个key出现的次数
#     key_counter = {}
#
#     for dict_item in dict_list:
#         for key in dict_item.keys():
#             key_counter[key] = key_counter.get(key, 0) + 1
#
#     # print(f"总共有 {len(key_counter)} 个不同的key")
#
#     # 找出重复的key
#     duplicate_keys = {key for key, count in key_counter.items() if count > 1}
#     # print(f"发现 {len(duplicate_keys)} 个重复key: {list(duplicate_keys)}")
#
#     # 第二步：合并字典，跳过重复key
#     merged_result = {}
#     skipped_count = 0
#
#     for dict_item in dict_list:
#         for key, value in dict_item.items():
#             if key in duplicate_keys:
#                 skipped_count += 1
#                 # print(f"跳过重复key: {key} (出现 {key_counter[key]} 次)")
#             elif key not in merged_result:  # 确保不重复添加
#                 merged_result[key] = value
#
#     # print(f"跳过了 {skipped_count} 个重复key的条目")
#     # print(f"合并后剩余 {len(merged_result)} 个唯一key")
#
#     return merged_result

def remove_twice_face(dict_list):
    """
    处理字典列表，排除重复的'old_face_nodes'，并合并成二维字典

    参数:
        dict_list: 字典列表，每个字典包含'old_face_nodes'等键

    返回:
        一个二维字典，其中第一级key是old_face_nodes的值（转换为元组），
        第二级是原始字典本身
    """
    if not dict_list:
        return {}

    # 步骤1：统计每个old_face_nodes出现的次数
    old_face_nodes_count = {}

    for item in dict_list:
        old_nodes = item.get('old_face_nodes')
        old_nodes = normalize_face_nodes(old_nodes)
        if old_nodes is not None:
            # 将列表转换为元组，因为列表不能作为字典的key
            key = tuple(old_nodes)
            old_face_nodes_count[key] = old_face_nodes_count.get(key, 0) + 1

    # 步骤2：过滤出只出现一次的old_face_nodes
    unique_old_nodes = {key for key, count in old_face_nodes_count.items() if count == 1}

    # 步骤3：筛选出对应的字典，并构建二维字典
    result_dict = {}

    for item in dict_list:
        old_nodes = item.get('old_face_nodes')
        old_nodes = normalize_face_nodes(old_nodes)
        if old_nodes is not None:
            key = tuple(old_nodes)
            if key in unique_old_nodes:
                # 以old_face_nodes的元组形式作为key，原始字典作为value
                result_dict[key] = item

    return result_dict


def update_element57_faces(element57, old_face_node_ids, new_face_nodes1, new_face_nodes2):
    """
    把57号多面体单元的其中一个面替换成两个新的面

    Args:
        element57: 原始的57号多面体单元对象
        old_face_nodes: 需要替换的面节点编号列表（整数列表）
        new_face_nodes1: 替换成的新的面节点对象列表1（从邻居单元获取，方向朝外）
        new_face_nodes2: 替换成的新的面节点对象列表2（从邻居单元获取，方向朝外）

    Returns:
        new_element57: 更新后的57号多面体单元
    """

    # 1. 复制原始单元
    new_element57 = element57

    normalized_old_face_node_ids = normalize_face_nodes(old_face_node_ids)

    # 3. 查找要替换的面
    face_index_to_replace = -1

    for i, face_nodes in enumerate(element57.mianDian):
        current_face_node_ids = [node.node_id for node in face_nodes]
        if normalize_face_nodes(current_face_node_ids) == normalized_old_face_node_ids:
            # print("找到需要替换的面")
            # print(normalized_old_face_node_ids)
            face_index_to_replace = i
            break

    if face_index_to_replace == -1:
        return None

    # 4. 简单反序新面节点（从朝外变为朝内）
    reversed_face1 = new_face_nodes1[::-1]  # 使用切片反序
    reversed_face2 = new_face_nodes2[::-1]
    # print("新面1")
    # print([node.node_id for node in reversed_face1])
    # print("新面2")
    # print([node.node_id for node in reversed_face2])

    # 5. 替换面
    new_faces = []
    for i, face_nodes in enumerate(new_element57.mianDian):
        if i == face_index_to_replace:
            new_faces.append(reversed_face1)
            new_faces.append(reversed_face2)
        else:
            new_faces.append(face_nodes)

    # 6. 更新单元属性
    new_element57.mianDian = new_faces
    new_element57.mian = [len(face) for face in new_faces]
    new_element57.mian_num = len(new_faces)

    new_element57.points = []
    for k in range(new_element57.mian_num):
        new_element57.points.extend(new_element57.mianDian[k])
    new_element57.num_point = len(new_element57.points)

    new_element57.ensure_faces_point_outward()
    new_element57.clip = 0

    return new_element57


def find_new_nodes(old_face_nodes, new_face_nodes1, new_face_nodes2, tolerance=1e-6):
    """
    old_face_nodes: 旧节点node列表
    new_face_nodes1: 新节点node列表1
    new_face_nodes2: 新节点node列表2

    任务：
    上面三个列表中的元素node，有node.x, node.y, node.z，表示坐标；node.node_id表示节点id
    遍历new_face_nodes1和new_face_nodes2的坐标，把坐标和old_face_nodes中的node坐标进行比较
    只把old_face_nodes中没出现的坐标的node放入字典new_add_nodes_map {node_id: Node对象}
    new_face_nodes1和new_face_nodes2坐标重复的node只需要取其中一个
    """
    new_add_nodes_map = {}

    # 检查坐标是否近似相等的辅助函数
    def is_same_coord(coord1, coord2, tol=tolerance):
        x1, y1, z1 = coord1
        x2, y2, z2 = coord2
        return (abs(x1 - x2) < tol and
                abs(y1 - y2) < tol and
                abs(z1 - z2) < tol)

    # 检查坐标是否在集合中（带容差）
    def coord_in_set(coord, coord_set, tol=tolerance):
        for existing_coord in coord_set:
            if is_same_coord(coord, existing_coord, tol):
                return True
        return False

    # 创建旧节点坐标的集合
    old_coords_set = set()
    for node in old_face_nodes:
        coord_key = (node.x, node.y, node.z)
        old_coords_set.add(coord_key)

    # 用于跟踪已添加的坐标（带容差检查）
    added_coords_list = []  # 使用列表存储已添加的坐标

    # 处理 new_face_nodes1
    for node in new_face_nodes1:
        coord_key = (node.x, node.y, node.z)

        # 检查是否在旧节点中已存在（带容差）
        if coord_in_set(coord_key, old_coords_set, tolerance):
            continue

        # 检查是否已经添加过（带容差）
        if coord_in_set(coord_key, added_coords_list, tolerance):
            continue

        # 添加到结果字典和已添加列表
        new_add_nodes_map[node.node_id] = node
        added_coords_list.append(coord_key)

    # 处理 new_face_nodes2
    for node in new_face_nodes2:
        coord_key = (node.x, node.y, node.z)

        # 检查是否在旧节点中已存在（带容差）
        if coord_in_set(coord_key, old_coords_set, tolerance):
            continue

        # 检查是否已经添加过（带容差）
        if coord_in_set(coord_key, added_coords_list, tolerance):
            continue

        # 添加到结果字典和已添加列表
        new_add_nodes_map[node.node_id] = node
        added_coords_list.append(coord_key)

    return new_add_nodes_map