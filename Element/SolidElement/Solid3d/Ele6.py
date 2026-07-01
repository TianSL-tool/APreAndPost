import numpy as np
import pyvista as pv

from Element.SolidElement.Solid3d.SolidElement3d import SolidElement3D


class ElementType6(SolidElement3D):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id)
        self.num_point =8

    def read_points(self, parts, node_map):
        self.points = [node_map[node_id] for node_id in parts[:8]]
        self.num_point = len(self.points)
        # for point in self.points:
        #     if point.node_id == 22393:
        #         print("read_points:",id(point))
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
        a, b, c = plane_normal
        d = -np.dot(plane_normal, plane_origin)  # 由 plane_normal · plane_origin + d = 0 得

        for node in self.points:
            # 计算节点到平面的距离：|ax + by + cz + d| / sqrt(a² + b² + c²)
            numerator = abs(a * node.x + b * node.y + c * node.z + d)
            denominator = np.linalg.norm(plane_normal)
            if denominator < 1e-10:
                break
            distance = numerator / denominator
            if distance <= tolerance:
                node.clip = 1



        # 转换单个单元为 pyvista UnstructuredGrid
        points = np.array([[node.x, node.y, node.z] for node in self.points])
        num_faces = 6
        cell_types = [pv.CellType.POLYHEDRON]
        cell = [num_faces]

        # 面信息
        faces = [
            [3, 2, 1, 0],
            [4, 5, 6, 7],
            [0, 4, 7, 3],
            [3, 7, 6, 2],
            [2, 6, 5, 1],
            [1, 5, 4, 0]
        ]

        for face in faces:
            num_face_nodes = len(face)
            cell.extend([num_face_nodes] + face)

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

            if positive_part is None or positive_element is None:
                negative_element.clip = 1
                return negative_element, None
            elif negative_part is None or negative_element is None:
                positive_element.clip = 1
                return positive_element, None
            else:
                if negative_element is None or positive_element is None:
                    print(self.e_id)
                positive_element.clip = 1
                negative_element.clip = 1
                return positive_element, negative_element
    # ####################################################################################################
    # 检索边界
    # ####################################################################################################
    def get_hexa_edges(self):
        """
        提取六面体单元的12条棱边（基于6号单元的8个顶点索引）
        返回：棱边列表，每条棱边是 (顶点1索引, 顶点2索引)
        六面体顶点索引定义（默认）：
        points[0]：底面左下前，points[1]：底面右下前，points[2]：底面右上后，points[3]：底面左上后
        points[4]：顶面左下前，points[5]：顶面右下前，points[6]：顶面右上后，points[7]：顶面左上后
        """
        return [
            # 底面4条边（z最小面）
            (0, 1), (1, 2), (2, 3), (3, 0),
            # 顶面4条边（z最大面）
            (4, 5), (5, 6), (6, 7), (7, 4),
            # 侧面4条边（连接底面和顶面）
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]

    def is_point_on_hexa_edge(self, new_node,max_line_size, tolerance=1e-8):
        """
        判定新增节点是否在六面体单元的某条棱边上
        :param new_node: 新增节点（Node对象，需包含x、y、z属性）
        :param tolerance: 浮点精度容差
        :return: (是否在边上, 所在边的两个顶点对象) → (bool, (node1, node2) or None)
        """
        dx = new_node.x - self.center[0]
        dy = new_node.y - self.center[1]
        dz = new_node.z - self.center[2]

        if np.sqrt(dx**2 + dy**2 + dz**2) > max_line_size:
            return False,None
        # 步骤1：获取六面体的所有棱边（索引对）
        hexa_edges = self.get_hexa_edges()
        # 步骤2：遍历每条棱边，验证新增节点是否在该边上
        for edge_idx1, edge_idx2 in hexa_edges:
            # 获取棱边的两个顶点对象

            edge_node1 = self.points[edge_idx1]
            edge_node2 = self.points[edge_idx2]
            if edge_node1.node_id == edge_node2.node_id:
                continue
            # ----------------------
            # 条件1：新增节点与棱边共线（向量叉积模长 < 容差）
            # ----------------------
            # 计算棱边向量：edge_vec = edge_node2 - edge_node1
            edge_vec = np.array([
                edge_node2.x - edge_node1.x,
                edge_node2.y - edge_node1.y,
                edge_node2.z - edge_node1.z
            ])
            # 计算新增节点到edge_node1的向量：point_vec = new_node - edge_node1
            point_vec = np.array([
                new_node.x - edge_node1.x,
                new_node.y - edge_node1.y,
                new_node.z - edge_node1.z
            ])
            # 叉积的模长：若为0，说明两向量共线
            cross_norm = np.linalg.norm(np.cross(edge_vec, point_vec))
            if cross_norm > tolerance:
                continue  # 不共线，跳过当前边

            # ----------------------
            # 条件2：新增节点在线段edge_node1-edge_node2范围内
            # ----------------------
            # 点积：point_vec · edge_vec → 若在0~|edge_vec|²之间，说明点在线段上
            dot_product = np.dot(point_vec, edge_vec)
            edge_len_sq = np.dot(edge_vec, edge_vec)  # 棱边长度的平方
            # 允许微小误差（如dot_product略小于0或略大于edge_len_sq）
            if (dot_product >= -tolerance) and (dot_product <= edge_len_sq + tolerance):
                return True, (edge_node1, edge_node2)  # 找到所在边

        # 遍历所有边后仍未匹配
        return False, None



    def change_boundary_element(self,new_add_nodes_map,max_line_size):
        if self.clip==2:
            for node in new_add_nodes_map.values():
                result,edge = self.is_point_on_hexa_edge(node, max_line_size, tolerance=1e-8)
                if result:
                    new_element=self.to_element57()
                    new_element.clip=3
                    new_element.change_boundary_element(new_add_nodes_map,max_line_size)
                    return new_element
            return self
        else:
            return self


    # ####################################################################################################
    # 更改单元类型，将6转为57
    # ####################################################################################################
    def get_6type_basic_faces(self):
        """预设6号单元的6个基础面（基于8个节点索引）"""
        return [
            [0, 1, 2, 3],  # 底面
            [4, 5, 6, 7],  # 顶面
            [0, 4, 7, 3],  # 侧面1
            [3, 7, 6, 2],  # 侧面2
            [2, 6, 5, 1],  # 侧面3
            [1, 5, 4, 0]  # 侧面4
        ]

    def deduplicate_face_nodes_by_id(self, face_node_indices):
        """
        对单个面的节点去重（通过node_id判定，相同node_id视为重复）
        :param face_node_indices: 面的节点索引列表（基于6号单元的8个节点）
        :return: 去重后的节点对象列表（node_id唯一）
        """
        deduplicated_nodes = []
        seen_ids = set()  # 记录已出现的node_id
        for idx in face_node_indices:
            current_node = self.points[idx]
            # 若node_id未出现过，保留该节点
            if current_node.node_id not in seen_ids:
                seen_ids.add(current_node.node_id)
                deduplicated_nodes.append(current_node)
        return deduplicated_nodes

    def adjust_face_direction(self, face_nodes):
        """调整面的节点顺序，确保右手定则指向单元外侧（逻辑不变）"""
        if len(face_nodes) < 3:
            return face_nodes

        # 计算单元中心和面中心
        elem_center = np.mean([[node.x, node.y, node.z] for node in self.points], axis=0)
        face_center = np.mean([[node.x, node.y, node.z] for node in face_nodes], axis=0)

        # 计算面的法向量（基于前3个节点）
        p0, p1, p2 = face_nodes[0], face_nodes[1], face_nodes[2]
        v1 = np.array([p1.x - p0.x, p1.y - p0.y, p1.z - p0.z])
        v2 = np.array([p2.x - p0.x, p2.y - p0.y, p2.z - p0.z])
        face_normal = np.cross(v1, v2)
        face_normal = face_normal / np.linalg.norm(face_normal) if np.linalg.norm(face_normal) > 1e-10 else np.zeros(3)

        # 调整方向（指向外侧）
        center_vec = elem_center - face_center
        if np.dot(face_normal, center_vec) > 0:
            return face_nodes[::-1]  # 反转顺序
        return face_nodes

    def to_element57(self):
        """6号单元转57号单元（通过node_id去重，无需容差）"""
        # 步骤1：获取6号单元的6个基础面
        basic_faces = self.get_6type_basic_faces()

        # 步骤2：处理每个面（去重→筛选有效面→调整方向）
        valid_faces = []
        for face_indices in basic_faces:
            # 2.1 通过node_id去重当前面的节点
            deduplicated_nodes = self.deduplicate_face_nodes_by_id(face_indices)
            # 2.2 筛选有效面（≥3个节点）
            if len(deduplicated_nodes) < 3:
                continue
            # 2.3 调整面方向（确保指向外侧）
            adjusted_face = self.adjust_face_direction(deduplicated_nodes)
            valid_faces.append(adjusted_face)

        # 步骤3：去重57号单元的所有节点（按node_id）
        unique_nodes = []
        seen_node_ids = set()
        for face in valid_faces:
            for node in face:
                # if node.node_id not in seen_node_ids:
                #     seen_node_ids.add(node.node_id)
                unique_nodes.append(node)

        # 步骤4：组织57号单元的面数据
        mian = [len(face) for face in valid_faces]  # 每个面的节点数
        mianDian = valid_faces  # 每个面的节点对象列表

        # 步骤5：创建57号单元实例并赋值
        from Element.ElementFactory import ElementFactory
        element57 = ElementFactory.create_element(self.e_id, 57, self.c_id, self.m_id, self.d_id, self.f_id)
        element57.mian_num = len(valid_faces)
        element57.mian = mian
        element57.mianDian = mianDian
        element57.points = unique_nodes
        element57.num_point = len(unique_nodes)
        # print(self.e_id)
        # for point in element57.points:
        #     print(point.node_id)
        return element57