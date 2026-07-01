import numpy as np
import pyvista as pv
from Element.SlipElement.Slip3d.SlipElement3d import SlipElement3D


class ElementType60(SlipElement3D):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__( e_id, t_id, c_id, m_id, d_id, f_id)
        self.half_num = None

    def read_points(self, parts, node_map):
        # 假设节点数是偶数，前半部分是底面节点，后半部分是顶面节点
        half_num = len(parts) // 2
        bottom_nodes = [node_map[node_id] for node_id in parts[:half_num]]
        top_nodes = [node_map[node_id] for node_id in parts[half_num:]]
        self.points = bottom_nodes + top_nodes
        self.num_point = len(self.points)

    def write_to_file(self, file):
        point_str = [str(point.node_id) for point in self.points]
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{int(p):10d}" for p in point_str]
        file.write(' '.join(formatted_info) + '\n')

    def get_write_string(self):
        point_str = [str(point.node_id) for point in self.points]
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{int(p):10d}" for p in point_str]
        return ' '.join(formatted_info)
    def cut_by_plane(self, plane_origin, plane_normal,max_e_id,tolerance=1.0e-3):
        # 转换单个单元为 pyvista UnstructuredGrid
        points = np.array([[node.x, node.y, node.z] for node in self.points])
        num_nodes = len(self.points)
        half_num = num_nodes // 2

        # 构建面信息
        num_faces = half_num + 2
        cell_types = [pv.CellType.POLYHEDRON]
        cell = [num_faces]

        # 底面
        bottom_face = list(range(half_num))[::-1]
        cell.extend([half_num] + bottom_face)

        # 顶面
        top_face = list(range(half_num, num_nodes))
        cell.extend([half_num] + top_face)

        # 侧面
        for i in range(half_num):
            side_face = [i, (i + 1) % half_num, (i + 1) % half_num + half_num, i + half_num]
            cell.extend([4] + side_face)

        cells = np.array([len(cell)] + cell)
        grid = pv.UnstructuredGrid(cells, cell_types, points)

        # 裁剪网格
        positive_part = grid.clip(normal=plane_normal, origin=plane_origin, invert=False)
        negative_part = grid.clip(normal=plane_normal, origin=plane_origin, invert=True)

        # 判断是否切割到单元
        if positive_part.n_points == 0 or negative_part.n_points == 0:
            # 没切割到，返回原单元
            return self, None
        else:
            # 切割到了，返回切割后的两个新单元
            positive_element = self.convert_grid_to_element(positive_part, self.e_id, tolerance)
            negative_element = self.convert_grid_to_element(negative_part, self.e_id + max_e_id,tolerance)
            if positive_part is None:
                negative_element.clip = 1
                return negative_element, None
            elif negative_part is None:
                positive_element.clip = 1
                return positive_element, None
            else:
                positive_element.clip = 1
                negative_element.clip = 1
                return positive_element, negative_element

    def change_boundary_element(self, new_add_nodes_map, max_line_size):
        if self.clip == 2 or self.clip == 3:
            return self.change_boundary_element_s(new_add_nodes_map, max_line_size)
        else:
            return self
    def change_boundary_element_s(self, new_add_nodes_map, max_line_size):
        """
        60号单元专属边界处理：仅插入新增节点到底面/顶面，更新points列表
        核心：保留原始排序，不拆分面，不新增属性
        """
        # 步骤1：拆分当前points为底面和顶面（基于half_num）
        current_bottom = self.points[:self.half_num]
        current_top = self.points[self.half_num:]

        # 步骤2：筛选“距离合规且在棱边上”的新增节点
        valid_add_nodes = self._filter_valid_nodes(
            new_add_nodes_map,
            current_bottom,
            current_top,
            max_line_size
        )
        if not valid_add_nodes:
            return self  # 无有效节点，直接返回原单元

        # 步骤3：插入新增节点到底面/顶面（保留原始排序）
        updated_bottom = self._insert_to_face(current_bottom, valid_add_nodes)
        updated_top = self._insert_to_face(current_top, valid_add_nodes)

        # 步骤4：更新points列表（底面+顶面，保持原始顺序逻辑）
        self.points = updated_bottom + updated_top
        self.num_point = len(self.points)
        # 更新half_num（因底面节点数量可能增加）
        self.half_num = len(updated_bottom)

        return self

    def _filter_valid_nodes(self, new_add_nodes_map, bottom_face, top_face, max_line_size):
        """筛选条件：1. 距离单元中心≤max_line_size；2. 在底面或顶面的棱边上"""
        # 计算单元中心
        unit_center = np.mean([[n.x, n.y, n.z] for n in self.points], axis=0)
        valid_nodes = []

        # 收集底面和顶面的所有棱边（节点对象 tuple）
        bottom_edges = self._get_face_edges(bottom_face)
        top_edges = self._get_face_edges(top_face)
        all_edges = bottom_edges + top_edges

        for node in new_add_nodes_map.values():
            # 条件1：距离单元中心不超过阈值
            dist = np.linalg.norm([
                node.x - unit_center[0],
                node.y - unit_center[1],
                node.z - unit_center[2]
            ])
            if dist > max_line_size:
                continue

            # 条件2：在底面或顶面的棱边上
            for edge in all_edges:
                if self.is_point_on_edge(node, edge):
                    valid_nodes.append(node)
                    break  # 一个节点只属于一条棱边，避免重复添加

        return valid_nodes

    def _get_face_edges(self, face):
        """获取单个面的棱边（(node1, node2) 元组，用于判断点是否在边上）"""
        edges = []
        face_len = len(face)
        for i in range(face_len):
            node1 = face[i]
            node2 = face[(i + 1) % face_len]  # 面闭合（首尾相连）
            edges.append((node1, node2))
        return edges

    def _insert_to_face(self, face, add_nodes):
        """
        将新增节点插入到指定面（底面/顶面），保留原始节点顺序
        :param face: 原始面节点列表（已排序）
        :param add_nodes: 需插入的新增节点
        :return: 插入后的面节点列表（保持原始顺序）
        """
        updated_face = face.copy()  # 基于原始面复制，避免修改原列表
        for new_node in add_nodes:
            # 查找新节点所在的棱边索引（i：棱边起点，i+1：棱边终点）
            insert_pos = -1
            face_len = len(updated_face)
            for i in range(face_len):
                node1 = updated_face[i]
                node2 = updated_face[(i + 1) % face_len]
                if self.is_point_on_edge(new_node, (node1, node2)):
                    insert_pos = i + 1  # 插入到 node1 之后、node2 之前
                    break
            if insert_pos != -1:
                updated_face.insert(insert_pos, new_node)  # 保持原始顺序插入
        return updated_face

    def is_point_on_edge(self, new_node, edge, tolerance=1e-8):
        """判断点是否在棱边上（复用向量计算逻辑）"""
        node1, node2 = edge
        # 计算向量
        edge_vec = np.array([node2.x - node1.x, node2.y - node1.y, node2.z - node1.z])
        point_vec = np.array([new_node.x - node1.x, new_node.y - node1.y, new_node.z - node1.z])
        # 1. 叉乘模长≈0（共线）
        cross_norm = np.linalg.norm(np.cross(edge_vec, point_vec))
        if cross_norm > tolerance:
            return False
        # 2. 点乘在[0, 边长度平方]范围内（点在线段上）
        dot_product = np.dot(point_vec, edge_vec)
        edge_len_sq = np.dot(edge_vec, edge_vec)
        return (dot_product >= -tolerance) and (dot_product <= edge_len_sq + tolerance)
