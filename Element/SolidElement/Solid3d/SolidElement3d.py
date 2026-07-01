import numpy as np

from Element.BaseElement import Element

from Node.node import Node


class SolidElement3D(Element):
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
    def subtract_initial_stress(self):
        """将当前应力数据减去初始应力值（应力列表的第一步），并更新self.stresses"""
        # 确保应力列表有数据
        if not self.stresses:
            print("错误：应力列表为空")
            return False

        # 获取应力列表的第一步作为初始应力
        first_step_stress = np.array(self.stresses[0]).reshape(1, 6, 1)

        # 转换当前应力为numpy数组
        current_stresses = np.array(self.stresses).reshape(-1, 6, 1)

        # 从每一步应力中减去初始应力
        updated_stresses = current_stresses - first_step_stress

        # 更新self.stresses（转换回列表格式）
        self.stresses = updated_stresses.reshape(-1, 6).tolist()

        return True

    def subtract_initial_strain(self):
        if not self.strains:
            print("错误：应力列表为空")
            return False

        # 获取应力列表的第一步作为初始应力
        first_step_strain = np.array(self.strains[0]).reshape(1, 6, 1)

        # 转换当前应力为numpy数组
        current_strain = np.array(self.strains).reshape(-1, 6, 1)

        # 从每一步应力中减去初始应力
        updated_strain = current_strain - first_step_strain

        # 更新self.stresses（转换回列表格式）
        self.strains = updated_strain.reshape(-1, 6).tolist()

        return True

    def calc_principle_stresses(self,podu=0):
        stresses = -np.array(self.stresses).reshape(-1, 6, 1)

        s11 = stresses[:, 0, 0]
        s22 = stresses[:, 1, 0]
        s33 = stresses[:, 2, 0]
        s12 = stresses[:, 3, 0]
        s23 = stresses[:, 4, 0]
        s31 = stresses[:, 5, 0]

        p = (s11 + s22 + s33) /3
        J2 = ((s11 - s22) ** 2 + (s11 - s33) ** 2 + (s22 - s33) ** 2) / 6 + (s12 ** 2 + s23 ** 2 + s31 ** 2)
        q = np.sqrt(3 * J2)

        if podu == 0:
            stress_d1 = s11 * 0.0
            stress_d2 = s11 * 0.0
            stress_d3 = s11 * 0.0
        else:
            cosA = podu / np.sqrt(podu * podu + 1)
            sinA = 1 / np.sqrt(podu * podu + 1)
            stress_d1 = s22 * sinA * sinA + s11 * cosA * cosA + s12 * sinA * cosA * 2
            stress_d2 = s33
            stress_d3 = s11 * sinA * sinA + s22 * cosA * cosA - s12 * sinA * cosA * 2

        self.principle_stress = np.column_stack((p, q)).tolist()
        self.stress_d1 =stress_d1.tolist()
        self.stress_d2 =stress_d2.tolist()
        self.stress_d3 =stress_d3.tolist()

        if p.size > 0:
            self.max_p = np.max(p)
            self.min_p = np.min(p)
        if q.size > 0:
            self.max_q = np.max(q)
            self.min_q = np.min(q)
        if stress_d1.size > 0:
            self.max_stress_d1 = np.max(stress_d1)
            self.min_stress_d1 = np.min(stress_d1)
        if stress_d2.size > 0:
            self.max_stress_d2 = np.max(stress_d2)
            self.min_stress_d2 = np.min(stress_d2)
        if stress_d3.size > 0:
            self.max_stress_d3 = np.max(stress_d3)
            self.min_stress_d3 = np.min(stress_d3)
    def get_majorstress_variable(self):
        stresses = np.array(self.stresses)
        stress_matrices = -np.array([[[s[0], s[3], s[5]], [s[3], s[1], s[4]], [s[5], s[4], s[2]]] for s in stresses])
        eigenvalues = np.linalg.eigvals(stress_matrices)
        sorted_eigenvalues = np.sort(eigenvalues)[:, ::-1]
        self.major_stress = sorted_eigenvalues.tolist()
        self.max_major_stresses = np.max(sorted_eigenvalues, axis=0).tolist()
        self.min_major_stresses = np.min(sorted_eigenvalues, axis=0).tolist()
    def calc_principle_strains(self):
        strains = -np.array(self.strains).reshape(-1, 6, 1)
        e11 = strains[:, 0, 0]
        e22 = strains[:, 1, 0]
        e33 = strains[:, 2, 0]
        e12 = strains[:, 3, 0] * 0.5
        e23 = strains[:, 4, 0] * 0.5
        e31 = strains[:, 5, 0] * 0.5


        p = (e11 + e22 + e33)/3
        I1 = p * 3
        J2 = ((e11 - e22) ** 2 + (e11 - e33) ** 2 + (e22 - e33) ** 2) / 6 + (e12 ** 2 + e23 ** 2 + e31 ** 2)
        gamma = np.sqrt(4 / 3 * J2)
        self.principle_strains = np.column_stack((I1, gamma)).tolist()
        if I1.size > 0:
            self.max_epsv = np.max(I1)
            self.min_epsv = np.min(I1)
        if gamma.size > 0:
            self.max_epss = np.max(gamma)
            self.min_epss = np.min(gamma)

    def get_majorstrain_variable(self):
        strains = np.array(self.strains)
        strain_matrices = -np.array([[[s[0], s[3] * 0.5, s[5] * 0.5], [s[3] * 0.5, s[1], s[4] * 0.5],
                                      [s[5] * 0.5, s[4] * 0.5, s[2]]] for s in strains])
        eigenvalues = np.linalg.eigvals(strain_matrices)
        sorted_eigenvalues = np.sort(eigenvalues)[:, ::-1]
        self.major_strain = sorted_eigenvalues.tolist()
        self.max_major_strain = np.max(sorted_eigenvalues, axis=0).tolist()
        self.min_major_strain = np.min(sorted_eigenvalues, axis=0).tolist()

    def get_maxandmin_stressandstrain(self):
        stresses = -np.array(self.stresses).reshape(-1, 6, 1)
        s11 = stresses[:, 0, 0]
        s22 = stresses[:, 1, 0]
        s33 = stresses[:, 2, 0]
        s12 = stresses[:, 3, 0]
        s23 = stresses[:, 4, 0]
        s31 = stresses[:, 5, 0]

        stress_vars = [s11, s22, s33, s12, s23, s31]
        for var in stress_vars:
            min_val = np.min(var)
            max_val = np.max(var)
            self.min_stress.append(min_val)
            self.max_stress.append(max_val)


        strain = -np.array(self.strains).reshape(-1, 6, 1)
        st11 = strain[:, 0, 0]
        st22 = strain[:, 1, 0]
        st33 = strain[:, 2, 0]
        st12 = strain[:, 3, 0]
        st23 = strain[:, 4, 0]
        st31 = strain[:, 5, 0]

        strain_vars = [st11, st22, st33, st12, st23, st31]
        for var in strain_vars:
            min_val = np.min(var)
            max_val = np.max(var)
            self.min_strain.append(min_val)
            self.max_strain.append(max_val)

    def get_dynamic_shear(self):
        # 计算每个主应变组的动态剪切应变
        self.dynamic_shear_strain = [strain[0] - strain[2] for strain in self.major_strain]
        initial_value = self.dynamic_shear_strain[0]
        self.dynamic_shear_strain = [val - initial_value for val in self.dynamic_shear_strain]

        # 计算动态剪切应变的最大值
        if self.dynamic_shear_strain:
            self.max_dynamic_shear_strain = np.max(self.dynamic_shear_strain)


    def calculate_stress_strain_variables(self, podu=0, initial_stress=1, initial_strain=1):
        if initial_stress == 0:
            self.subtract_initial_stress()
        if initial_strain == 0:
            self.subtract_initial_strain()
        self.calc_principle_stresses(podu)
        self.calc_principle_strains()
        self.get_majorstress_variable()
        self.get_majorstrain_variable()
        self.get_maxandmin_stressandstrain()
        self.get_dynamic_shear()

    def write_ele_Schedule(self):
        elem_output_file = f"{self.e_id}.ele"
        with open(elem_output_file, 'w') as elem_file:
            if self.stresses or self.strains:
                elem_file.write("step\tsigx\tsigy\tsigz\ttaoxy\ttaoyz\ttaozx\tp\tq\tsig1\tsig2\tsig3\tsig_d1\tsig_d2\tsig_d3\t"
                                "epsx\tepsy\tepsz\ttaoxy\ttaoyz\ttaozx\tepsv\tepsq\teps1\teps2\teps3\tdynamic_shear_strain\n")
                # step_iter = self.steps if self.stresses else self.steps if self.strains else []
                step_iter = self.steps
                for step in step_iter:
                    stress = self.stresses[self.steps.index(step)] if self.stresses else [""] * 6
                    principle_stress = self.principle_stress[
                        self.steps.index(step)] if self.principle_stress else [""] * 3
                    major_stress = self.major_stress[self.steps.index(step)] if self.major_stress else [""]
                    strain = self.strains[self.steps.index(step)] if self.strains else [""] * 6
                    principle_strains = self.principle_strains[
                        self.steps.index(step)] if self.principle_strains else [""] * 3
                    major_strain = self.major_strain[self.steps.index(step)] if self.major_strain else [""]
                    dynamic_shear_strain = self.dynamic_shear_strain[
                        self.steps.index(step)] if self.dynamic_shear_strain else [""]

                    elem_file.write(f"{str(step)}\t")
                    elem_file.write(f"{' '.join(map(str, stress))}\t")
                    elem_file.write(f"{' '.join(map(str, principle_stress))}\t")
                    elem_file.write(f"{' '.join(map(str, major_stress))}\t")
                    elem_file.write(f" {self.stress_d1[self.steps.index(step)]}\t")
                    elem_file.write(f" {self.stress_d2[self.steps.index(step)]}\t")
                    elem_file.write(f" {self.stress_d3[self.steps.index(step)]}\t")
                    elem_file.write(f"{' '.join(map(str, strain))}\t")
                    elem_file.write(f"{' '.join(map(str, principle_strains))}\t")
                    elem_file.write(f"{' '.join(map(str, major_strain))}\t")
                    elem_file.write(f"{str(dynamic_shear_strain)}\n")


    def write_step(self,step,element_file):
        if step in self.steps:
            index = self.steps.index(step)
            element_file.write(f"Element {self.e_id}:\t")
            element_file.write(f"center\t")
            element_file.write(f"{' '.join(map(str, self.center))}\t")
            element_file.write(f"Stress\t")
            element_file.write(f"{' '.join(map(str, self.stresses[index]))}\t")
            element_file.write(f"VarStress\t")
            element_file.write(f"{' '.join(map(str, self.principle_stress[index]))}\t")
            element_file.write(f"MajorStress\t")
            element_file.write(f"{' '.join(map(str, self.major_stress[index]))}\t")
            element_file.write(f"stress_d1\t")
            element_file.write(f" {self.stress_d1[index]}\t")
            element_file.write(f"stress_d2\t")
            element_file.write(f" {self.stress_d2[index]}\t")
            element_file.write(f"stress_d3\t")
            element_file.write(f" {self.stress_d3[index]}\t")
            element_file.write(f"Strain\t")
            element_file.write(f"{' '.join(map(str, self.strains[index]))}\t")
            element_file.write(f"VarStrain\t")
            element_file.write(f"{' '.join(map(str, self.principle_strains[index]))}\t")
            element_file.write(f"MajorStrain\t")
            element_file.write(f"{' '.join(map(str, self.major_strain[index]))}\t")
            element_file.write(f"dynamic_shear_strain\t")
            element_file.write(f"{self.dynamic_shear_strain[index]}\n")

    def write_max_step(self,element_file):
        element_file.write(f"Element {self.e_id}:\t")
        element_file.write(f"center_coor\t")
        element_file.write(f"{' '.join(map(str, self.center))}\t")
        element_file.write(f"maxStress\t")
        element_file.write(f"{' '.join(map(str, self.max_stress))}\t")
        element_file.write(f"minStress\t")
        element_file.write(f"{' '.join(map(str, self.min_stress))}\t")
        element_file.write(f"max_p_q\t")
        element_file.write(f" {self.max_p}\t {self.max_q}\t")
        element_file.write(f"min_p_q\t")
        element_file.write(f" {self.min_p}\t {self.min_q}\t")
        element_file.write(f"maxMajorStress\t")
        element_file.write(f"{' '.join(map(str, self.max_major_stresses))}\t")
        element_file.write(f"minMajorStress\t")
        element_file.write(f"{' '.join(map(str, self.min_major_stresses))}\t")

        element_file.write(f"max_d\t")
        element_file.write(f" {self.max_stress_d1}\t {self.max_stress_d2}\t {self.max_stress_d3}\t")
        element_file.write(f"min_d\t")
        element_file.write(f" {self.min_stress_d1}\t {self.min_stress_d2}\t {self.min_stress_d3}\t")

        element_file.write(f"maxStrain\t")
        element_file.write(f"{' '.join(map(str, self.max_strain))}\t")
        element_file.write(f"minStrain\t")
        element_file.write(f"{' '.join(map(str, self.min_strain))}\t")
        element_file.write(f"max_epsv_eps_s\t")
        element_file.write(f" {self.max_epsv}\t {self.max_epss}\t")
        element_file.write(f"min_epsv_eps_s\t")
        element_file.write(f" {self.min_epsv}\t {self.min_epss}\t")
        element_file.write(f"maxMajorStrain\t")
        element_file.write(f"{' '.join(map(str, self.max_major_strain))}\t")
        element_file.write(f"minMajorStrain\t")
        element_file.write(f"{' '.join(map(str, self.min_major_strain))}\t")
        element_file.write(f"maxdynamic_shear_strain\t")
        element_file.write(f" {self.max_dynamic_shear_strain}\n")

    def cut_by_plane(self, plane_origin, plane_normal,max_e_id):
        pass


    def ensure_faces_point_outward(self):
        pass
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
                return None
        element.ensure_faces_point_outward()
        return element
