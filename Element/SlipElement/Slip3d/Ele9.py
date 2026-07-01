import numpy as np
import pyvista as pv

from Element.SlipElement.Slip3d.SlipElement3d import SlipElement3D


class ElementType9(SlipElement3D):
    def read_points(self, parts, node_map):
        self.points = [node_map[node_id] for node_id in parts[:8]]
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


    def cut_by_plane(self, plane_origin, plane_normal, max_e_id, tolerance=1.0e-3):
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

    def is_point_on_hexa_edge(self, new_node, max_line_size, tolerance=1e-8):
        """
        判断新增节点是否在9号单元（四边形）的某条棱边上，且距离单元中心≤max_line_size
        :param new_node: 待判断的新增节点
        :param max_line_size: 节点到单元中心的最大距离阈值
        :param tolerance: 几何计算容差
        :return: (result, edge) - result为bool（是否在棱边上），edge为所在棱边的节点对（(node1, node2)）
        """
        # 步骤1：计算单元中心（用于距离判断）
        unit_center = np.mean([[n.x, n.y, n.z] for n in self.points], axis=0)
        dist_to_center = np.linalg.norm([
            new_node.x - unit_center[0],
            new_node.y - unit_center[1],
            new_node.z - unit_center[2]
        ])
        if dist_to_center > max_line_size:
            return False, None  # 距离超标，直接返回

        # 步骤2：提取9号单元的4条棱边（四边形特性：4个节点，4条边）
        # 假设9号单元points顺序为 [p0, p1, p2, p3]，棱边为 p0-p1、p1-p2、p2-p3、p3-p0
        if len(self.points) != 8:
            return False, None  # 9号单元应为4节点四边形，不符合则返回
        if self.points[2].node_id == self.points[3].node_id:
            edges = [
                (self.points[0], self.points[1]),  # 棱边0：p0-p1
                (self.points[1], self.points[2]),  # 棱边1：p1-p2
                (self.points[2], self.points[0]),  # 棱边3：p3-p0
                (self.points[4], self.points[5]),  # 棱边0：p0-p1
                (self.points[5], self.points[6]),  # 棱边1：p1-p2
                (self.points[6], self.points[4]),  # 棱边2：p2-p3
            ]
        else:
            edges = [
                (self.points[0], self.points[1]),  # 棱边0：p0-p1
                (self.points[1], self.points[2]),  # 棱边1：p1-p2
                (self.points[2], self.points[3]),  # 棱边2：p2-p3
                (self.points[3], self.points[0]),  # 棱边3：p3-p0
                (self.points[4], self.points[5]),  # 棱边0：p0-p1
                (self.points[5], self.points[6]),  # 棱边1：p1-p2
                (self.points[6], self.points[7]),  # 棱边2：p2-p3
                (self.points[7], self.points[4])  # 棱边3：p3-p0
            ]


        # 步骤3：判断节点是否在某条棱边上
        for edge in edges:
            node1, node2 = edge
            # 向量计算：判断共线且点在线段范围内
            edge_vec = np.array([node2.x - node1.x, node2.y - node1.y, node2.z - node1.z])
            point_vec = np.array([new_node.x - node1.x, new_node.y - node1.y, new_node.z - node1.z])

            # 条件1：叉乘模长≈0（共线）
            cross_norm = np.linalg.norm(np.cross(edge_vec, point_vec))
            if cross_norm > tolerance:
                continue  # 不共线，跳过当前棱边

            # 条件2：点乘在[0, 棱边长度平方]范围内（点在线段上）
            dot_product = np.dot(point_vec, edge_vec)
            edge_len_sq = np.dot(edge_vec, edge_vec)
            if -tolerance <= dot_product <= edge_len_sq + tolerance:
                return True, edge  # 找到所在棱边

        # 未在任何棱边上
        return False, None
    def change_boundary_element(self,new_add_nodes_map,max_line_size):

        if self.clip==2:
            for node in new_add_nodes_map.values():
                result,edge = self.is_point_on_hexa_edge(node, max_line_size, tolerance=1e-8)
                if result:
                    new_element=self.to_element60()
                    new_element.clip=3
                    new_element.change_boundary_element(new_add_nodes_map,max_line_size)
                    return new_element
            return self
        else:
            return self

    def to_element60(self):
        """9号单元转60号单元（通过node_id去重，无需容差）"""
        # 步骤1：获取6号单元的6个基础面

        # 步骤5：创建57号单元实例并赋值
        from Element.ElementFactory import ElementFactory
        element60 = ElementFactory.create_element(self.e_id, 60, self.c_id, self.m_id, self.d_id, self.f_id)
        if self.points[2].node_id == self.points[3].node_id:
            element60.half_num = 3
            bottom_nodes = self.points[0:3]
            top_nodes = self.points[4:7]
            self.points = bottom_nodes + top_nodes
            self.num_point = len(self.points)
        else:
            element60.half_num =4
            element60.points = self.points
            element60.num_point = len(element60.points)
        return element60