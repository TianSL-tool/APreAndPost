import numpy as np
import pyvista as pv

from Element.SlipElement.Slip3d.SlipElement3d import SlipElement3D


class ElementType224(SlipElement3D):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id)
    def read_points(self, parts, node_map):
        self.num_mid = parts[:3]
        self.points = [node_map[node_id] for node_id in parts[3:]]
        self.num_point = len(self.points)
        print("224:", self.num_mid, self.points)
    def write_to_file(self, file):
        num_mid_str = [str(num) for num in self.num_mid]
        point_str = [str(point.node_id) for point in self.points]
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ]+ [f"{int(p):10d}" for p in num_mid_str] + [f"{int(p):10d}" for p in point_str]
        file.write(' '.join(formatted_info) + '\n')

    def get_write_string(self):
        num_mid_str = [str(num) for num in self.num_mid]
        point_str = [str(point.node_id) for point in self.points]
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{int(p):10d}" for p in num_mid_str] + [f"{int(p):10d}" for p in point_str]
        return ' '.join(formatted_info)