from Element.SolidElement.Solid3d.SolidElement3d import SolidElement3D


class ElementType508(SolidElement3D):
    def read_points(self, parts, node_map):
        # Number of faces and number of edges on each face.
        self.mian_num = parts[0]
        self.mian = parts[1:1 + self.mian_num]
        index = 1 + self.mian_num

        # Polynomial order of every edge, grouped by face.
        self.mian_order = []
        for edge_num in self.mian:
            face_orders = parts[index:index + edge_num]
            self.mian_order.append(face_orders)
            index += edge_num

        # Number of faces and number of edges on each face.????????????
        # A p-order edge adds p - 1 nodes, so a face has sum(orders) nodes.
        self.mianDian = []
        self.points = []
        for face_orders in self.mian_order:
            face_point_num = sum(face_orders)
            face_node_ids = parts[index:index + face_point_num]
            face_points = [node_map[node_id] for node_id in face_node_ids]
            self.mianDian.append(face_points)
            self.points.extend(face_points)
            index += face_point_num
        self.num_point = len(self.points)

    def write_to_file(self, file):
        point_info = (
            [self.mian_num]
            + self.mian
            + [order for face_orders in self.mian_order for order in face_orders]
            + [point.node_id for face in self.mianDian for point in face]
        )
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{value:10d}" for value in point_info]
        file.write(' '.join(formatted_info) + '\n')

    def get_write_string(self):
        point_info = (
            [self.mian_num]
            + self.mian
            + [order for face_orders in self.mian_order for order in face_orders]
            + [point.node_id for face in self.mianDian for point in face]
        )
        formatted_info = [
            f"{self.e_id:10d}",
            f"{self.t_id:10d}",
            f"{self.c_id:10d}",
            f"{self.m_id:10d}",
            f"{self.d_id:10d}",
            f"{self.f_id:10d}"
        ] + [f"{value:10d}" for value in point_info]
        return ' '.join(formatted_info)
