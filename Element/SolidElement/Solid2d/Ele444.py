from Element.SolidElement.Solid2d.SolidElement2d import SolidElement2D


class ElementType444(SolidElement2D):
    def read_points(self, parts, node_map):
        # 读取边的数量
        self.bian_num = parts[0]
        # 读取每条边包含的点数
        self.bian = parts[1:1 + self.bian_num]
        # 计算总点数
        self.num_point = 0
        for bian_num in self.bian:
            self.num_point += bian_num

        # 读取所有点的坐标（通过node_map映射）
        index = 1 + self.bian_num
        self.points = [node_map[node_id] for node_id in parts[index:index + self.num_point]]

        # ========== 新增：打印读取的关键信息 ==========
        print("=" * 50)  # 分隔线，方便区分输出
        print("【读取点数据信息】")
        print(f"1. 边的数量 (bian_num): {self.bian_num}")
        print(f"2. 每条边的点数 (bian): {self.bian}")
        print(f"3. 总点数 (num_point): {self.num_point}")
        print(f"4. 读取的节点ID范围: parts[{index}:{index + self.num_point}]")
        print(f"5. 读取的节点ID列表: {parts[index:index + self.num_point]}")
        print(f"6. 映射后的点坐标列表 (共{len(self.points)}个点):")
        # 逐个打印点坐标，方便核对
        for i, point in enumerate(self.points):
            print(f"   点{i + 1}: {point}")
        print("=" * 50)


    def write_to_file(self, file):
        point_str = [str(self.bian_num)] + [str(x) for x in self.bian] + [str(point.node_id) for point in self.points]
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
        point_str = [str(self.bian_num)] + [str(x) for x in self.bian] + [str(point.node_id) for point in self.points]
        formatted_info = [
                             f"{self.e_id:10d}",
                             f"{self.t_id:10d}",
                             f"{self.c_id:10d}",
                             f"{self.m_id:10d}",
                             f"{self.d_id:10d}",
                             f"{self.f_id:10d}"
                         ] + [f"{int(p):10d}" for p in point_str]
        return ' '.join(formatted_info)
