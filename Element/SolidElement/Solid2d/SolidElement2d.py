import math

import numpy as np

from Element.BaseElement import Element


class SolidElement2D(Element):
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
        first_step_stress = np.array(self.stresses[0]).reshape(1, 4, 1)

        # 转换当前应力为numpy数组
        current_stresses = np.array(self.stresses).reshape(-1, 4, 1)

        # 从每一步应力中减去初始应力
        updated_stresses = current_stresses - first_step_stress

        # 更新self.stresses（转换回列表格式）
        self.stresses = updated_stresses.reshape(-1, 4).tolist()

        return True

    def subtract_initial_strain(self):
        if not self.strains:
            print("错误：应力列表为空")
            return False

        # 获取应力列表的第一步作为初始应力
        first_step_strain = np.array(self.strains[0]).reshape(1, 3, 1)

        # 转换当前应力为numpy数组
        current_strain = np.array(self.strains).reshape(-1, 3, 1)

        # 从每一步应力中减去初始应力
        updated_strain = current_strain - first_step_strain

        # 更新self.stresses（转换回列表格式）
        self.strains = updated_strain.reshape(-1, 3).tolist()

        return True
    def calc_principle_stresses(self, podu=0, material=None):
        stresses = np.array(self.stresses)
        # 提取应力分量
        s11 = stresses[:, 0]
        s22 = stresses[:, 1]
        s33 = stresses[:, 2]
        s12 = stresses[:, 3]

        # 计算平均应力 p
        p = (s11 + s22 + s33) / 3
        # 计算 J2
        J2 = ((s11 - s22) ** 2 + (s11 - s33) ** 2 + (s22 - s33) ** 2) / 6 + (s12 ** 2 )
        # 计算 q
        q = np.sqrt(3 * J2)
        self.principle_stress = np.column_stack((p, q)).tolist()

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
        # 构建应力矩阵
        stress_matrices = -np.array([[[s[0], s[3], 0], [s[3], s[1], 0], [0, 0, s[2]]] for s in stresses])
        # 计算特征值
        eigenvalues = np.linalg.eigvals(stress_matrices)
        # 对特征值进行排序
        sorted_eigenvalues = np.sort(eigenvalues)[:, ::-1]
        self.major_stress = sorted_eigenvalues.tolist()
        self.max_major_stresses = np.max(sorted_eigenvalues, axis=0).tolist()
        self.min_major_stresses = np.min(sorted_eigenvalues, axis=0).tolist()

    def calc_principle_strains(self):
        strians0=np.copy(self.strains)
        for i in range(len(strians0)):
            for j in range(len(strians0[0])):
                strians0[i][j] =strians0[i][j]- self.strains[0][j]

        strains = np.array(strians0)

        # 提取应变分量
        e11 = strains[:, 0]
        e22 = strains[:, 1]
        e12 = strains[:, 2] * 0.5

        # 计算平均应变 p
        p = (e11 + e22 ) / 3
        # 计算 I1
        I1 = p * 3
        # 计算 J2
        J2 = ((e11 - e22) ** 2 + (e11) ** 2 + (e22) ** 2) / 6 + (e12 ** 2 )
        # 计算 gamma
        gamma = np.sqrt(4 / 3 * J2)
        self.principle_strains = np.column_stack((I1, gamma)).tolist()
        if I1.size > 0:
            self.max_epsv = np.max(I1)
            self.min_epsv = np.min(I1)
        if gamma.size > 0:
            self.max_epss = np.max(gamma)
            self.min_epss = np.min(gamma)

    def get_majorstrain_variable(self):
        strians0 = np.copy(self.strains)
        for i in range(len(strians0)):
            for j in range(len(strians0[0])):
                strians0[i][j] =strians0[i][j]- self.strains[0][j]

        strains = np.array(strians0)
        # 构建应变矩阵
        strain_matrices = -np.array([[[s[0], s[2] * 0.5, 0], [s[2] * 0.5, s[1], 0], [0, 0, 0]] for s in strains])
        # 计算特征值
        eigenvalues = np.linalg.eigvals(strain_matrices)
        # 对特征值进行排序
        sorted_eigenvalues = np.sort(eigenvalues)[:, ::-1]
        self.major_strain = sorted_eigenvalues.tolist()
        # print(self.major_strain)
        self.max_major_strain = np.max(sorted_eigenvalues, axis=0).tolist()
        self.min_major_strain = np.min(sorted_eigenvalues, axis=0).tolist()

    def get_maxandmin_stressandstrain(self):
        stresses = -np.array(self.stresses).reshape(-1, 4, 1)
        s11 = stresses[:, 0, 0]
        s22 = stresses[:, 1, 0]
        s33 = stresses[:, 2, 0]
        s12 = stresses[:, 3, 0]


        stress_vars = [s11, s22, s33, s12]
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

    def GetMaxShearStrain1(self, strain):
        PI = math.pi
        ROOT3 = math.sqrt(3)
        angle = 2.0 / 3.0 * PI

        nDim = 2
        nPlane = 0

        Epsx = 0.0
        Epsy = 0.0
        Epsz = 0.0
        Gammxy = 0.0
        Gammyz = 0.0
        Gammzx = 0.0

        if nDim == 2:
            if nPlane == 0:
                Epsx = strain[0]
                Epsy = strain[1]
                Gammxy = strain[2] * 0.5
                Epsz = 0.0
                Gammyz = 0.0
                Gammzx = 0.0

        elif nDim == 3:
            Epsx = strain[0]
            Epsy = strain[1]
            Epsz = strain[2]
            Gammxy = strain[3] * 0.5
            Gammyz = strain[4] * 0.5
            Gammzx = strain[5] * 0.5


        I1 = Epsx + Epsy + Epsz
        I1_2 = I1 * I1
        I1_3 = I1_2 * I1

        Gammxy_2 = Gammxy * Gammxy
        Gammyz_2 = Gammyz * Gammyz
        Gammzx_2 = Gammzx * Gammzx

        I2 = -Epsx * Epsy - Epsy * Epsz - Epsz * Epsx + Gammxy_2 + Gammyz_2 + Gammzx_2
        I3 = Epsx * Epsy * Epsz + 2.0 * Gammxy * Gammyz * Gammzx - Epsx * Gammyz_2 - Epsy * Gammzx_2 - Epsz * Gammxy_2

        J2 = I1_2 / 3.0 + I2
        if J2 < 0.0:
            J2 = 0.0

        SQRT_J2 = math.sqrt(J2)
        J3 = (I1_3 + I1_3 + 9.0 * I1 * I2 + 27.0 * I3) / 27.0

        if J2 <= 0.0:
            temp1 = 0.0
        else:
            temp1 = -1.5 * ROOT3 * J3 / (J2 * SQRT_J2)

        if temp1 > 1.0:
            temp1 = 1.0
        if temp1 < -1.0:
            temp1 = -1.0

        Theta = math.asin(temp1) / 3.0
        temp2 = 2.0 / ROOT3 * SQRT_J2
        Gamma_max = temp2 * (math.sin(Theta + angle) - math.sin(Theta - angle))

        return abs(Gamma_max)


    def GetMaxShearStrain2(self, strain):
        Epsx = strain[0]
        Epsy = strain[1]
        Gammxy = strain[2]
        Gamma_max = np.sqrt((Epsx-Epsy)*(Epsx-Epsy)+Gammxy*Gammxy)
        return abs(Gamma_max)

    def get_dynamic_shear(self):
        # 计算每个主应变组的动态剪切应变
        # strians0 = np.copy(self.strains)
        # for i in range(len(strians0)):
        #     for j in range(len(strians0[0])):
        #         strians0[i][j] = strians0[i][j] - self.strains[0][j]
        #     gamma1= self.GetMaxShearStrain1(strians0[i])
        #     gamma2 = self.GetMaxShearStrain2(strians0[i])
        #     self.dynamic_shear_strain1.append(gamma1)
        #     self.dynamic_shear_strain2.append(gamma2)

        for strain in self.major_strain:
            eps1 = strain[0]
            eps2 = strain[1]
            eps3 = strain[2]
            # J2=1/6*((eps1-eps2)**2+(eps1-eps3)**2+(eps3-eps1)**2)
            # gamma0=2*np.sqrt(J2/3)
            gamma0 = eps1-eps3
            self.dynamic_shear_strain.append(gamma0)


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
                elem_file.write("step\tsigx\tsigy\tsigz\ttaoxy\tp\tq\tsig1\tsig2\tsig3\tsig_d1\tsig_d2\tsig_d3\t"
                                "epsx\tepsy\ttaoxy\tepsp\tepsq\teps1\teps2\teps3\tdynamic_shear_strain\n")
                step_iter = self.steps if self.stresses else self.steps if self.strains else []
                for step in step_iter:
                    stress = self.stresses[self.steps.index(step)] if self.stresses else [""] * 4
                    principle_stress = self.principle_stress[
                        self.steps.index(step)] if self.principle_stress else [""] * 3
                    major_stress = self.major_stress[self.steps.index(step)] if self.major_stress else [""]
                    strain = self.strains[self.steps.index(step)] if self.strains else [""] * 3
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
        # element_file.write(f"maxdynamic_shear_strain1\t")
        # element_file.write(f" {self.max_dynamic_shear_strain1}\t")
        # element_file.write(f"maxdynamic_shear_strain2\t")
        # element_file.write(f" {self.max_dynamic_shear_strain2}\n")