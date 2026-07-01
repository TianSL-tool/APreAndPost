from abc import ABC, abstractmethod

import numpy as np

class Element(ABC):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        self.e_id = e_id
        self.t_id = t_id
        self.c_id = c_id
        self.m_id = m_id
        self.d_id = d_id
        self.f_id = f_id
        self.points = []
        self.num_point = 0
        self._center = None
        # 是否被切割，0是未被检索过，1是检索过被切割过，2是检索过在范围内，3是有节点在边上（6已经检索到了，转为57后不用再判别）
        self.clip = 0
        #     结果内容
        self.stresses = []
        self.strains = []
        self.dystresses = []
        self.dystrains =[]

        self.principle_stress = []
        self.principle_strains = []
        self.major_stress = []
        self.major_strain = []
        self.steps = []

        self.max_stress = []
        self.min_stress = []

        self.max_strain = []
        self.min_strain = []

        self.max_p = None
        self.min_p = None

        self.max_q = None
        self.min_q = None

        self.max_major_stresses = []
        self.min_major_stresses = []

        self.max_epsv = None
        self.min_epsv = None

        self.max_epss = None
        self.min_epss = None

        self.max_major_strain = []
        self.min_major_strain = []

        self.dynamic_shear_strain = []
        self.dynamic_shear_strain1 = []
        self.dynamic_shear_strain2 = []
        self.max_dynamic_shear_strain = None

    @property
    def center(self):
        if self._center is None:
            unique_points_dict = {}
            for point in self.points:
                rounded_x = round(point.x, 8)
                rounded_y = round(point.y, 8)
                rounded_z = round(point.z, 8)
                key = (rounded_x, rounded_y, rounded_z)
                unique_points_dict[key] = point

            unique_points = list(unique_points_dict.values())
            # 计算单元的中心

            self._center = np.mean([[node.x, node.y, node.z] for node in unique_points], axis=0)
        return self._center

    @abstractmethod
    def read_points(self, parts, node_map):
        pass

    @abstractmethod
    def write_to_file(self, file):
        pass

    @abstractmethod
    def get_write_string(self):
        pass
    @abstractmethod
    def calculate_stress_strain_variables(self, podu=0, initial_stress=1, initial_strain=1):
        pass
    @abstractmethod
    def write_ele_Schedule(self):
        pass

    @abstractmethod
    def write_step(self,step,element_file):
        pass

    @abstractmethod
    def write_max_step(self, element_file):
        pass







