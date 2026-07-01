import numpy as np

from Element.SlipElement.Slip2d.SlipElement2d import SlipElement2D



class ElementType4(SlipElement2D):
    def __init__(self, e_id, t_id, c_id, m_id, d_id, f_id):
        super().__init__( e_id, t_id, c_id, m_id, d_id, f_id)
        self.half_num = None

    def read_points(self, parts, node_map):
        # 假设节点数是偶数，前半部分是底面节点，后半部分是顶面节点
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

