import numpy as np

from Element.BaseElement import Element

from Node.node import Node

class SlipElement3D(Element):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id)

    def read_points(self, parts, node_map):
        self.points = [node_map[node_id] for node_id in parts]
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

    # def get_normal_vector(self):
    #     face_points = np.array([[point.x, point.y, point.z] for point in self.points])
    #     # 顶面法向量需与目标法向量同向（核心特性修改）
    #     v1 = face_points[1] - face_points[0]
    #     v2 = face_points[2] - face_points[1]
    #     face_normal = np.cross(v1, v2)
    #     face_normal_unit = face_normal / np.linalg.norm(face_normal)
    #     return face_normal_unit

    def get_normal_vector(self):
        face_points = np.array([[point.x, point.y, point.z] for point in self.points])
        n_points = len(face_points)

        # 至少需要3个不共线的点才能计算法向量
        if n_points < 3:
            raise ValueError("计算法向量至少需要3个点，当前仅提供{}个点".format(n_points))

        # 定义要尝试的三点组合（优先常用组合，顺序可根据实际场景调整）
        # 假设 self.points 是面的顶点（通常≥3个），组合需覆盖所有可能的不共线情况
        point_combinations = [
            (0, 1, 2),  # 默认组合
            (0, 2, 3),  # 换用第3个点
            (1, 2, 3),  # 换用第0个点
            (0, 1, 3),  # 换用第2个点
            (0, 3, 4)  # 若有5个点，补充组合（根据实际顶点数扩展）
        ]

        # 数值精度阈值（避免因浮点数误差误判共线，可根据场景调整，如1e-6）
        epsilon = 1e-5

        face_normal = None
        for i, j, k in point_combinations:
            # 确保组合的索引不超出点的数量
            if i >= n_points or j >= n_points or k >= n_points:
                continue

            # 取当前组合的三个点，计算两个边向量
            p0, p1, p2 = face_points[i], face_points[j], face_points[k]
            v1 = p1 - p0
            v2 = p2 - p0  # 优化：统一以p0为起点，计算更稳定

            # 计算叉乘，判断是否共线（叉乘模长接近0则共线）
            cross_product = np.cross(v1, v2)
            cross_norm = np.linalg.norm(cross_product)

            if cross_norm > epsilon:
                # 非共线，可计算法向量
                face_normal = cross_product / cross_norm
                break

        # 若所有组合都共线，抛出异常（说明这不是一个合法的面）
        if face_normal is None:
            raise RuntimeError("所有点都共线，无法计算法向量。当前点集：{}".format(face_points))

        # （可选）确保法向量与目标方向一致（根据你的业务需求补充）
        # target_normal = np.array([0, 0, 1])  # 示例：目标法向量（如朝上）
        # if np.dot(face_normal, target_normal) < 0:
        #     face_normal = -face_normal  # 反向，使其与目标方向同向

        return face_normal

    def get_maxandmin_stressandstrain(self):
        stresses = -np.array(self.stresses).reshape(-1, 3, 1)
        s11 = stresses[:, 0, 0]
        s22 = stresses[:, 1, 0]
        s33 = stresses[:, 2, 0]

        stress_vars = [s11, s22, s33]
        for var in stress_vars:
            min_val = np.min(var)
            max_val = np.max(var)
            self.min_stress.append(min_val)
            self.max_stress.append(max_val)

        strain = -np.array(self.strains).reshape(-1, 3, 1)
        st11 = strain[:, 0, 0]
        st22 = strain[:, 1, 0]
        st33 = strain[:, 2, 0]

        strain_vars = [st11, st22, st33]
        for var in strain_vars:
            min_val = np.min(var)
            max_val = np.max(var)
            self.min_strain.append(min_val)
            self.max_strain.append(max_val)

    def calculate_stress_strain_variables(self, podu=0, initial_stress=1, initial_strain=1):
        self.get_maxandmin_stressandstrain()

    def write_ele_Schedule(self,podu=0.0):
        elem_output_file = f"{self.e_id}.ele"
        with open(elem_output_file, 'w') as elem_file:
            if self.stresses or self.strains:
                elem_file.write("step\tShearStresse1\tShearStresse2\tNormalStresse2\tShearDisp1\tShearDisp2\tNormalDisp\n")
                # step_iter = self.steps if self.stresses else self.steps if self.strains else []
                step_iter = self.steps
                for step in step_iter:
                    stress = self.stresses[self.steps.index(step)] if self.stresses else [""] * 3
                    strain = self.strains[self.steps.index(step)] if self.strains else [""] * 3
                    elem_file.write(f"{str(step)}\t")
                    elem_file.write(f"{' '.join(map(str, stress))}\t")
                    elem_file.write(f"{' '.join(map(str, strain))}\n")



    def write_step(self,step,element_file):
        if step in self.steps:
            index = self.steps.index(step)
            element_file.write(f"Element {self.e_id}:\t")
            element_file.write(f"center\t")
            element_file.write(f"{' '.join(map(str, self.center))}\t")
            element_file.write(f"Stress\t")
            element_file.write(f"{' '.join(map(str, self.stresses[index]))}\t")
            element_file.write(f"Strain\t")
            element_file.write(f"{' '.join(map(str, self.strains[index]))}\n")


    def write_max_step(self,element_file):
        element_file.write(f"Element {self.e_id}:\t")
        element_file.write(f"center_coor\t")
        element_file.write(f"{' '.join(map(str, self.center))}\t")
        element_file.write(f"maxStress\t")
        element_file.write(f"{' '.join(map(str, self.max_stress))}\t")
        element_file.write(f"minStress\t")
        element_file.write(f"{' '.join(map(str, self.min_stress))}\t")
        element_file.write(f"maxStrain\t")
        element_file.write(f"{' '.join(map(str, self.max_strain))}\t")
        element_file.write(f"minStrain\t")
        element_file.write(f"{' '.join(map(str, self.min_strain))}\n")


    def convert_grid_to_element(self, grid, new_e_id,tolerance):
        new_nodes = []
        new_node_map = {}
        existing_nodes = self.points  # 只遍历切割前当前单元的节点

        for i, point in enumerate(grid.points):
            new_node = Node(i + 1, point[0], point[1], point[2])
            found = False
            for existing_node in existing_nodes:
                distance = np.linalg.norm(np.array([new_node.x, new_node.y, new_node.z]) - np.array(
                    [existing_node.x, existing_node.y, existing_node.z]))
                if distance < tolerance:
                    new_node = existing_node
                    found = True
                    break
            if not found:
                new_nodes.append(new_node)
                new_node_map[i] = new_node
            else:
                new_node_map[i] = new_node
        from Element.ElementFactory import ElementFactory
        element = ElementFactory.create_element(new_e_id, 57, self.c_id, self.m_id, self.d_id, self.f_id)

        if grid.n_cells > 0:
            cell = grid.get_cell(0)
            faces = cell.faces
            face_nodes = []
            valid_faces = []
            valid_face_counts = []

            # 处理每个面
            for face in faces:
                # 去掉重复节点
                unique_nodes = []
                for node_id in face.point_ids:
                    if new_node_map[node_id] not in unique_nodes:
                        unique_nodes.append(new_node_map[node_id])

                # 记录缩并重复节点后的点数
                num_unique_nodes = len(unique_nodes)

                # 如果节点数大于等于 2，则保留该面
                if num_unique_nodes > 2:
                    valid_faces.append(unique_nodes)
                    valid_face_counts.append(num_unique_nodes)

            element.mian_num = len(valid_faces)
            element.mian = valid_face_counts
            element.mianDian = valid_faces
            element.points = [node for face in valid_faces for node in face]
            element.num_point = len(element.points)
            if element.mian_num<=3:
                raise ValueError("切割后面的数量小于3")
                # return None

        return element.turn_57_to_60(self.get_normal_vector())
        # return element
    def change_boundary_element(self,new_add_nodes_map,max_line_size):
        return self