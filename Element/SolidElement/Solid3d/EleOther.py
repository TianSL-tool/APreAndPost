import numpy as np
import pyvista as pv

from Element.SolidElement.Solid3d.SolidElement3d import SolidElement3D


class OtherElementType(SolidElement3D):
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
                return negative_element, None
            elif negative_part is None:
                return positive_element, None
            else:
                return positive_element, negative_element
