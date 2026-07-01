import numpy as np
import pyvista as pv
from Element.SolidElement.Solid3d.SolidElement3d import SolidElement3D
# from Element.ElementFactory import ElementFactory

class ElementType57or59(SolidElement3D):
    def read_points(self, parts, node_map):
        self.mian_num = parts[0]
        self.mian = parts[1:1 + self.mian_num]
        self.mianDian = [[] for _ in range(self.mian_num)]
        index = 1 + self.mian_num
        for k in range(self.mian_num):
            self.mianDian[k] = [node_map[node_id] for node_id in parts[index:index + self.mian[k]]]
            self.points.extend(self.mianDian[k])
            index += self.mian[k]
        self.num_point = len(self.points)


    def write_to_file(self, file):
        point_str = [str(self.mian_num)] + [str(x) for x in self.mian] + [str(point.node_id) for point in self.points]
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
        point_str = [str(self.mian_num)] + [str(x) for x in self.mian] + [str(point.node_id) for point in self.points]
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
        num_faces = self.mian_num
        cell_types = [pv.CellType.POLYHEDRON]
        cell = [num_faces]
        for face in self.mianDian:
            num_face_nodes = len(face)
            cell.extend([num_face_nodes])
            for node in face:
                cell.append(self.points.index(node))
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


    def ensure_faces_point_outward(self):
        for i, face in enumerate(self.mianDian):
            # 获取面的顶点坐标
            face_points = np.array([[node.x, node.y, node.z] for node in face])
            # 计算面的中心
            face_center = np.mean(face_points, axis=0)
            # 计算面的法向量
            v1 = face_points[1] - face_points[0]
            v2 = face_points[2] - face_points[0]
            face_normal = np.cross(v1, v2)
            # 计算从单元中心到面中心的向量
            center_to_face = face_center - self.center
            # 判断法向量方向是否正确
            if np.dot(face_normal, center_to_face) < 0:
                # 反转面的顶点顺序
                self.mianDian[i] = face[::-1]
        self.points = [node for face in self.mianDian for node in face]

    def turn_57_to_60(self, vector_normal):
        """
        将57号多面体单元转换为60号接触面单元（适配新特性）
        特性：底面与顶面法向量同向，底面法向量指向顶面，节点排序一致（第一条边方向相同）
        参数:
            vector_normal: 底面法向量（已知，指向顶面方向）
        """
        self.ensure_faces_point_outward()  # 确保原始面法向量正确

        bottom_face = None  # 底面
        top_face = None  # 顶面
        bottom_idx = -1
        bottom_normal = None

        # 步骤1：识别底面（法向量与目标同向，后续用于定位顶面）
        for i, face in enumerate(self.mianDian):
            face_points = np.array([[n.x, n.y, n.z] for n in face])
            # 计算面法向量（右手定则）
            v1 = face_points[1] - face_points[0]
            v2 = face_points[2] - face_points[1]
            face_normal = np.cross(v1, v2)
            face_norm_long = np.linalg.norm(face_normal)


            if face_norm_long > 1.0e-6:
                # 非共线，可计算法向量
                face_normal_unit = face_normal / face_norm_long  # 单位化
            else:
                v1 = face_points[2] - face_points[1]
                v2 = face_points[3] - face_points[2]
                face_normal = np.cross(v1, v2)
                face_norm_long = np.linalg.norm(face_normal)
                face_normal_unit = face_normal / face_norm_long

            # 底面法向量需与目标法向量同向
            if is_same_direction(face_normal_unit, vector_normal, 5):
                bottom_face = face
                bottom_idx = i
                bottom_normal = face_normal_unit
                break

        if bottom_face is None:
            raise ValueError("未找到与目标法向量同向的底面")

        # 步骤2：识别顶面（法向量同向+位置相对+底面指向顶面）


        for i, face in enumerate(self.mianDian):
            if i == bottom_idx:
                continue  # 跳过底面

            face_points = np.array([[n.x, n.y, n.z] for n in face])
            # 顶面法向量需与目标法向量同向（核心特性修改）
            v1 = face_points[1] - face_points[0]
            v2 = face_points[2] - face_points[1]
            face_normal = np.cross(v1, v2)
            face_normal_unit = face_normal / np.linalg.norm(face_normal)

            if is_same_direction(face_normal_unit, -vector_normal, 5):
                top_face = face
                top_idx = i
                top_normal = face_normal_unit
                break  # 法向量不同向，排除

        if top_face is None:
            raise ValueError("未找到符合条件的顶面（法向量同向且底面指向顶面）")

        # 步骤3：验证并调整顶面节点顺序（确保第一条边方向与底面一致）
        adjusted_top = self._match_edge_direction(bottom_face, top_face)
        bottom_center = np.mean([[n.x, n.y, n.z] for n in bottom_face], axis=0)
        top_center = np.mean([[n.x, n.y, n.z] for n in bottom_face], axis=0)
        v = top_center - bottom_center

        # 步骤4：重构60号单元属性
        from Element.ElementFactory import ElementFactory
        element = ElementFactory.create_element(self.e_id, 60, self.c_id, self.m_id, self.d_id, self.f_id)
        if is_same_direction(face_normal_unit, vector_normal, 5):
            element.points = bottom_face + adjusted_top
        else:
            element.points = adjusted_top + bottom_face

        element.num_point = len(element.points)
        return element

    def _match_edge_direction(self, bottom_face, top_face):
        """
        调整顶面节点顺序，确保第一条边方向与底面一致（核心匹配逻辑）
        第一条边：face[0] -> face[1] 的向量方向需基本相同
        """
        if len(bottom_face) != len(top_face):
            raise ValueError(f"底面与顶面节点数量不一致（{len(bottom_face)} vs {len(top_face)}）")

        # 提取底面第一条边向量
        bottom_p0 = np.array([bottom_face[0].x, bottom_face[0].y, bottom_face[0].z])
        bottom_p1 = np.array([bottom_face[1].x, bottom_face[1].y, bottom_face[1].z])
        bottom_edge = bottom_p1 - bottom_p0
        bottom_edge_unit = bottom_edge / np.linalg.norm(bottom_edge)

        # 尝试旋转顶面节点，找到第一条边方向匹配的排列
        top_nodes = top_face.copy()
        node_count = len(top_nodes)


        # 尝试反转后再旋转（应对镜像情况）
        reversed_top = top_nodes[::-1]
        for shift in range(node_count):
            shifted_top = reversed_top[shift:] + reversed_top[:shift]
            top_p0 = np.array([shifted_top[0].x, shifted_top[0].y, shifted_top[0].z])
            top_p1 = np.array([shifted_top[1].x, shifted_top[1].y, shifted_top[1].z])
            top_edge = top_p1 - top_p0
            top_edge_unit = top_edge / np.linalg.norm(top_edge)

            if is_same_direction(top_edge_unit, bottom_edge_unit, 5):
                return shifted_top

        raise ValueError("无法匹配底面与顶面的第一条边方向")


    # ####################################################################################################
    # 检索边界
    # ####################################################################################################
    def change_boundary_element(self, new_add_nodes_map, max_line_size):
        # print(new_add_nodes_map)
        # print(max_line_size)
        if self.clip == 2 or self.clip == 3:
            return self.change_boundary_element_s(new_add_nodes_map, max_line_size)
        else:
            return self

    def get_all_edges(self):
        """
        提取单元所有棱边（基于面的节点ID，避免重复）
        每条棱边用 tuple(节点1ID, 节点2ID) 表示（ID1 <= ID2 确保唯一性）
        """
        edges = set()  # 用节点ID的元组存储棱边，避免Node对象不可哈希的问题
        for face in self.mianDian:
            num_nodes = len(face)
            for i in range(num_nodes):
                # 获取当前节点和下一个节点的ID（而非节点对象）
                node1_id = face[i].node_id
                node2_id = face[(i+1) % num_nodes].node_id  # 面的节点首尾相连
                # 按ID排序，确保棱边表示唯一（如(1,2)和(2,1)视为同一条条边）
                if node1_id <= node2_id:
                    edge = (node1_id, node2_id)
                else:
                    edge = (node2_id, node1_id)
                edges.add(edge)  # 节点ID的元组是可哈希的，可存入set
        return edges  # 返回棱边的ID元组集合

    def is_point_on_edge(self, new_node, edge, tolerance=1e-8):
        node1_id, node2_id = edge  # edge是(node1_id, node2_id)元组
        # 显式比较node_id（避免触发__eq__的坐标比较）
        node1 = next((n for n in self.points if n.node_id == node1_id), None)
        node2 = next((n for n in self.points if n.node_id == node2_id), None)
        if not node1 or not node2:
            return False  # 棱边节点不存在

        # 后续向量计算逻辑不变...
        edge_vec = np.array([node2.x - node1.x, node2.y - node1.y, node2.z - node1.z])
        point_vec = np.array([new_node.x - node1.x, new_node.y - node1.y, new_node.z - node1.z])
        cross_norm = np.linalg.norm(np.cross(edge_vec, point_vec))
        if cross_norm > tolerance:
            return False
        dot_product = np.dot(point_vec, edge_vec)
        edge_len_sq = np.dot(edge_vec, edge_vec)
        return (dot_product >= -tolerance) and (dot_product <= edge_len_sq + tolerance)

    def get_face_containing_edge(self, edge):
        """
        找到包含某条棱边的所有面（棱边用ID元组表示）
        :param edge: 棱边 (node1_id, node2_id)
        :return: 包含该棱边的面列表（面是节点对象列表）
        """
        node1_id, node2_id = edge
        containing_faces = []
        for face in self.mianDian:
            # 检查面中是否同时存在两个节点ID，且相邻
            ids = [n.node_id for n in face]
            if node1_id in ids and node2_id in ids:
                idx1 = ids.index(node1_id)
                idx2 = ids.index(node2_id)
                if (abs(idx1 - idx2) == 1) or (abs(idx1 - idx2) == len(face) - 1):
                    containing_faces.append(face)
        return containing_faces

    def sort_face_nodes_ccw(self, face_nodes):
        """
        按右手定则（指向外侧）对面向量排序
        :param face_nodes: 面的节点对象列表（含新增节点）
        :return: 排序后的节点列表
        """
        if len(face_nodes) < 3:
            return face_nodes

        # 单元中心
        elem_center = np.mean([[n.x, n.y, n.z] for n in self.points], axis=0)
        # 面中心
        face_center = np.mean([[n.x, n.y, n.z] for n in face_nodes], axis=0)
        center_vec = face_center - elem_center  # 面中心到单元中心的向量

        normal = None
        # 遍历所有可能的三点组合，寻找不共线的组合计算法向量
        n = len(face_nodes)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    p0, p1, p2 = face_nodes[i], face_nodes[j], face_nodes[k]
                    # 计算两个边向量
                    v1 = np.array([p1.x - p0.x, p1.y - p0.y, p1.z - p0.z])
                    v2 = np.array([p2.x - p0.x, p2.y - p0.y, p2.z - p0.z])
                    # 计算叉乘（法向量）
                    current_normal = np.cross(v1, v2)
                    norm = np.linalg.norm(current_normal)
                    # 若法向量非零（三点不共线），则使用该法向量
                    if norm > 1e-6:
                        normal = current_normal / norm  # 归一化
                        break  # 跳出k循环
                if normal is not None:
                    break  # 跳出j循环
            if normal is not None:
                break  # 跳出i循环

        # 若所有点共线（理论上多边形面不会出现这种情况）
        if normal is None:
            return face_nodes  # 返回原始列表

        # 调整方向：确保法向量指向外侧（与单元中心方向一致）
        if np.dot(normal, center_vec) < 0:
            return face_nodes[::-1]  # 反转顺序使法向量朝外
        return face_nodes

    def insert_node_in_face(self, face, new_node):
        """
        将新增节点插入面的节点列表（插入到所在棱边的两个节点之间）
        :param face: 原面节点列表
        :param new_node: 新增节点
        :return: 插入后的面节点列表（未排序）
        """
        # 找到新增节点所在的棱边（在当前面中）
        face_edges = []
        num_nodes = len(face)
        for i in range(num_nodes):
            node1 = face[i]
            node2 = face[(i + 1) % num_nodes]
            face_edges.append((node1, node2))

        # 确定新增节点所在的棱边索引
        target_edge_idx = -1
        for i, edge in enumerate(face_edges):
            if self.is_point_on_edge(new_node, edge):
                target_edge_idx = i
                break
        if target_edge_idx == -1:
            return face  # 未找到所在棱边，返回原面

        # 插入到棱边的两个节点之间（node1之后，node2之前）
        node1 = face[target_edge_idx]
        node2 = face[(target_edge_idx + 1) % num_nodes]
        new_face = []
        for i, node in enumerate(face):
            new_face.append(node)
            if node == node1 and face[(i + 1) % num_nodes] == node2:
                new_face.append(new_node)  # 插入新增节点
        return new_face


    def split_face_by_two_nodes(self, face, nodeA, nodeB):
        """
        将面按两个新增节点拆分为两个子面
        示例：A-B-C-D-E，nodeA=node1（C-D上），nodeB=node2（D-E上）
        期望输出：[A-B-C-node1-node2-E, node1-D-node2]
        """
        num_nodes = len(face)
        if num_nodes < 3:
            return [face]  # 非多边形，无法拆分

        # 构建棱边列表：(起点, 终点)，记录nodeA/nodeB所在棱边
        idxA = -1  # nodeA在棱边(face[idxA], face[idxA+1])上
        idxB = -1  # nodeB在棱边(face[idxB], face[idxB+1])上
        for i in range(num_nodes):
            p, q = face[i], face[(i + 1) % num_nodes]
            if self.is_point_on_edge(nodeA, (p, q)):
                idxA = i
            if self.is_point_on_edge(nodeB, (p, q)):
                idxB = i
        if idxA == -1 or idxB == -1:
            print("节点不在面上")
            return [face]  # 节点不在面上
        if idxA == idxB:
            print("同棱边无法拆分")
            return [face]  # 同棱边无法拆分

        # 确保idxA在idxB之前（按面的顺序，如示例中idxA=2（C-D），idxB=3（D-E））
        # 若面是顺时针，可能需要调整顺序，这里假设面是逆时针（A-B-C-D-E顺序）
        if (idxA) % num_nodes > (idxB) % num_nodes:
            idxA, idxB = idxB, idxA
            nodeA, nodeB = nodeB, nodeA
        # print("idxA nodeA:",idxA,nodeA.node_id)
        # print("idxB nodeB:",idxB,nodeB.node_id)
        # 路径1：外环（A-B-C-node1-node2-E）
        path1 = []
        # 1. 从起点到nodeA的前序节点（A-B-C）
        i = 0
        while i <= idxA:
            path1.append(face[i])
            i += 1
        # 2. 加入nodeA（C之后是node1）
        path1.append(nodeA)
        # 3. 跳过原棱边中间节点（C-D中的D暂不加入，后续通过nodeB衔接）
        # 4. 加入nodeB（node1之后是node2）
        # （若idxA和idxB之间有其他节点，需加入，示例中idxA=2，idxB=3，无中间节点）
        # i = idxA + 1
        # while i < idxB:
        #     path1.append(face[i])
        #     i += 1
        # 5. 加入nodeB（D之后是node2）
        path1.append(nodeB)
        # 6. 从nodeB的后序节点到终点（E，回到A形成闭环）
        i = idxB + 1
        while i < num_nodes:
            path1.append(face[i])
            i += 1
        # 闭合路径（最后一个节点连接到第一个节点，排序时会自动处理）

        # 路径2：内环（node1-D-node2）
        path2 = []
        # 1. 从nodeA开始
        path2.append(nodeA)
        # 2. 加入idxA和idxB之间的原节点（C-D和D-E之间的D）
        i = idxA + 1
        while i <= idxB:
            path2.append(face[i])
            i += 1
        # 3. 加入nodeB
        path2.append(nodeB)
        # 闭合路径（nodeB连接回nodeA）
        path2.append(nodeA)
        # for node in face:
        #     print("原始:",node.node_id)
        # for node in path1:
        #     print("path1:",node.node_id)
        # for node in path2:
        #     print("path2:",node.node_id)
        # 去重（避免重复节点，如闭合时的起点）
        path1 = list(dict.fromkeys(path1))
        path2 = list(dict.fromkeys(path2))

        # 排序（确保是闭合多边形，若原方法可靠）
        sorted1 = self.sort_face_nodes_ccw(path1)
        sorted2 = self.sort_face_nodes_ccw(path2)

        return [sorted1, sorted2]

    def split_face_by_index_and_point(self, face, idxA, nodeB):
        """
        用面上节点的索引idxA（节点A）和边上新增点B拆分面
        若两者在同一条棱上则无法切割
        :param face: 原面节点列表（如[A, B, C, D, E]）
        :param idxA: 节点A在face中的索引（如A的索引为0）
        :param nodeB: 插入到面的某条棱边上的新增点（如D-E棱上的node2）
        :return: 两个子面节点列表，若同棱则返回原面
        """
        num_nodes = len(face)
        if num_nodes < 3:
            return [face]  # 非多边形无法拆分

        # 验证idxA的有效性
        if not (0 <= idxA < num_nodes):
            print(f"索引idxA={idxA}无效，超出面节点范围")
            return [face]

        # ----------------------
        # 1. 定位点B所在棱边索引idxB
        # ----------------------
        idxB = -1
        for i in range(num_nodes):
            p, q = face[i], face[(i + 1) % num_nodes]
            if self.is_point_on_edge(nodeB, (p, q)):
                idxB = i
                break
        if idxB == -1:
            print("点B不在面上")
            return [face]

        # ----------------------
        # 2. 判断A（idxA）和B（idxB）是否在同一条棱上
        # 节点A属于两条棱边：(idxA-1)和idxA（索引）
        # ----------------------
        a_edge1 = (idxA - 1) % num_nodes  # A的前一条棱边索引
        a_edge2 = idxA  # A的后一条棱边索引
        if idxB in [a_edge1, a_edge2]:
            print(f"节点A（索引{idxA}）和点B在同一条棱上（棱边索引{idxB}），无法切割")
            return [face]

        # ----------------------
        # 3. 确保idxA在idxB的“前方”（按面的顺序）
        # ----------------------
        if idxA % num_nodes > idxB % num_nodes:
            # 交换后仍保持idxA是原节点索引，nodeB是边点
            # print(f"A在后面")
            # print("idxA 和 idxB",idxA,idxB)
            path1 = []
            path2 = []
            path1 = face[:idxB + 1] + [nodeB] + face[idxA:]
            # path2.append()
            path2 =[nodeB] +face[idxB + 1:idxA + 1]
        else:
            # print(f"A在前面")
            path1 = []
            path2 = []
            path1 = face[:idxA+1]+[nodeB]+face[idxB+1:]
            path2 = face[idxA:idxB+1]
            path2.append(nodeB)
            # 注意：此处仅交换索引，nodeB无需交换（因B是边点）

        # ----------------------
        # 6. 去重并排序
        # ----------------------
        # for node in face:
        #     print("原始:",node.node_id)
        # for node in path1:
        #     print("path1:",node.node_id)
        # for node in path2:
        #     print("path2:",node.node_id)
        path1 = list(dict.fromkeys(path1))
        path2 = list(dict.fromkeys(path2))

        sorted1 = self.sort_face_nodes_ccw(path1)
        sorted2 = self.sort_face_nodes_ccw(path2)

        return [sorted1, sorted2]


    def change_boundary_element_s(self, new_add_nodes_map, max_line_size):
        """
        处理边界单元：判断新增节点是否在单元上，单节点重排面，双节点拆分面
        :param new_add_nodes_map: 新增节点字典 {node_id: Node对象}
        :param max_line_size: 节点到单元中心的最大距离阈值
        """
        # 步骤1：筛选在单元棱边上的新增节点（且距离单元中心≤max_line_size）
        unit_center = np.mean([[n.x, n.y, n.z] for n in self.points], axis=0)
        on_unit_nodes = []  # 在单元上的新增节点
        edges = self.get_all_edges()  # 单元所有棱边

        for node in new_add_nodes_map.values():
            # 距离单元中心是否超过阈值
            dist_to_center = np.linalg.norm([
                node.x - unit_center[0],
                node.y - unit_center[1],
                node.z - unit_center[2]
            ])
            if dist_to_center > max_line_size:
                continue

            # 判断是否在任意棱边上
            for edge in edges:
                if self.is_point_on_edge(node, edge):
                    on_unit_nodes.append(node)
                    break

        if not on_unit_nodes:
            return self# 无新增节点在单元上，直接返回

        # 步骤2：按面分组（同一面的新增节点放在一组）
        face_node_groups = {}  # key: 原面节点列表的id，value: 该面的新增节点列表
        for face in self.mianDian:
            face_id = id(face)  # 用内存地址作为唯一标识
            face_node_groups[face_id] = []
            # 检查每个新增节点是否在当前面的任意棱边上
            for node in on_unit_nodes:
                for i in range(len(face)):
                    edge = (face[i], face[(i + 1) % len(face)])
                    if self.is_point_on_edge(node, edge):
                        face_node_groups[face_id].append(node)
                        break

        # 步骤3：处理每个面的新增节点
        new_mianDian = []  # 新的面列表
        new_mian = []  # 新的面节点数列表

        for face in self.mianDian:
            face_id = id(face)
            nodes_on_face = face_node_groups.get(face_id, [])
            # 去重同一面的新增节点（按node_id）
            unique_nodes = []
            seen_ids = set()
            clip_node=None
            for node in nodes_on_face:
                # if node.node_id not in seen_ids:
                #     seen_ids.add(node.node_id)
                unique_nodes.append(node)
            nodes_on_face = unique_nodes
            if len(nodes_on_face) == 0:
                # 无新增节点，保留原面
                new_mianDian.append(face)
                new_mian.append(len(face))
            elif len(nodes_on_face) == 1:
                # 单节点：插入面并排序
                # print("插入单个节点")
                for i in range(len(face)):
                    if face[i].clip == 1:
                        clip_node = i
                        # print("被切割的节点：", face[i].node_id)
                        break
                if clip_node is None:
                    new_node = nodes_on_face[0]
                    inserted_face = self.insert_node_in_face(face, new_node)
                    sorted_face = self.sort_face_nodes_ccw(inserted_face)
                    new_mianDian.append(sorted_face)
                    new_mian.append(len(sorted_face))
                else:
                    print("split_face_by_index_and_point:")
                    nodeB= nodes_on_face[0]
                    # nodeB= face[clip_node]
                    # new_face = face[:clip_node] + face[clip_node+1:]
                    sub_faces = self.split_face_by_index_and_point(face, clip_node, nodeB)
                    for sub_face in sub_faces:
                        new_mianDian.append(sub_face)
                        new_mian.append(len(sub_face))
            elif len(nodes_on_face) >= 2:
                # 多节点：取前两个节点拆分面（若有更多节点可递归处理）
                nodeA, nodeB = nodes_on_face[0], nodes_on_face[1]
                # 检查是否为同一点（node_id相同）
                if nodeA.node_id == nodeB.node_id:
                    # 视为单节点处理
                    inserted_face = self.insert_node_in_face(face, nodeA)
                    sorted_face = self.sort_face_nodes_ccw(inserted_face)
                    new_mianDian.append(sorted_face)
                    new_mian.append(len(sorted_face))
                else:

                    sub_faces = self.split_face_by_two_nodes(face, nodeA, nodeB)
                    for sub_face in sub_faces:
                        new_mianDian.append(sub_face)
                        new_mian.append(len(sub_face))

        # print("原本：",  self.mian_num)
        # print("现在：", len(new_mianDian))
        # 更新单元的面数据
        self.mianDian = new_mianDian
        self.mian = new_mian
        self.mian_num = len(new_mianDian)

        # 更新单元的节点列表（包含新增节点）
        all_nodes = []
        seen_ids = set()
        for face in self.mianDian:
            for node in face:
                # if node.node_id not in seen_ids:
                #     seen_ids.add(node.node_id)
                all_nodes.append(node)
        self.points = all_nodes
        self.num_point = len(all_nodes)

        return self






def vector_angle(a, b, eps=1e-8):
    """
    计算两个向量之间的夹角

    参数:
        a, b: 输入的两个向量（NumPy数组）
        degrees: 是否返回角度（默认False，返回弧度）
        eps: 浮点计算误差阈值（默认1e-8）

    返回:
        两向量的夹角（弧度或角度）
    """
    # 计算点积
    dot_product = np.dot(a, b)

    # 计算模长
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    # 处理零向量（模长为0时无法计算夹角）
    if norm_a < eps or norm_b < eps:
        raise ValueError("输入向量不能为零向量")

    # 计算余弦值（夹在[-1, 1]之间，避免因浮点误差超出范围）
    cos_theta = dot_product / (norm_a * norm_b)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)  # 限制范围，防止arccos报错

    # 计算弧度
    theta_rad = np.arccos(cos_theta)

    # 转换为角度
    return np.rad2deg(theta_rad)
def is_same_direction(a, b, eps=1):
    # 计算点积
    theta = vector_angle(a,b)
    if theta <=eps:
        return True
    else:
        return False

def is_opposite_direction(a, b, eps=1e-6):
    # 计算点积
    dot_product = np.dot(a, b)
    # 计算模长乘积的负值
    neg_norm_product = -np.linalg.norm(a) * np.linalg.norm(b)
    # 检查是否近似相等（考虑浮点误差）
    return np.isclose(dot_product, neg_norm_product, atol=eps)


