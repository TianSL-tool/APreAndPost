import numpy as np


class Node:
    def __init__(self, node_id, x=0, y=0, z=0, ux=0, uy=0, uz=0, press=0, rx=0, ry=0, rz=0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.z = z
        self.ux = ux
        self.uy = uy
        self.uz = uz
        self.press = press
        self.rx = rx
        self.ry = ry
        self.rz = rz
        self.coord = np.array([x, y, z], dtype=np.float64)  # 坐标向量
        self.clip = 0
        # 结果内容
        self.disp = []
        self.poress = []
        self.acc = []
        self.vel = []
        self.steps = []

        self.max_disp = []
        self.min_disp = []
        self.max_disp_abs = []
        self.max_acc = []
        self.min_acc = []
        self.max_acc_abs = []
        self.max_vel = []
        self.min_vel = []
        self.max_vel_abs = []
        self.max_poress = None
        self.min_poress = None



    def __eq__(self, other):
        """
        修正相等性判断：
        - 与Node实例比较：比较坐标（保持原有逻辑）
        - 与整数比较：比较node_id
        - 其他类型：返回False
        """
        if isinstance(other, Node):
            # 与另一个Node对象比较：判断坐标是否相等（原有逻辑）
            return (self.x == other.x and
                    self.y == other.y and
                    self.z == other.z)
        elif isinstance(other, int):
            # 与整数比较：判断node_id是否相等
            return self.node_id == other
        else:
            # 其他类型（如字符串、None等）：不相等
            return False

    # 可选：添加__hash__方法（若需要将Node作为字典键）
    def __hash__(self):
        return hash(self.node_id)

    def calc_max_min(self):
        dim = len(self.disp[0])
        if dim==3:
            disp = -np.array(self.disp).reshape(-1, 3, 1)
            dispx = disp[:, 0, 0]
            dispy = disp[:, 1, 0]
            dispz = disp[:, 2, 0]

            disp_vars = [dispx, dispy, dispz]
            for var in disp_vars:
                min_val = np.min(var)
                max_val = np.max(var)
                abs_max_val = max(np.abs(max_val),np.abs(min_val))
                self.max_disp.append(max_val)
                self.min_disp.append(min_val)
                self.max_disp_abs.append(abs_max_val)
            if self.acc:
                acc = -np.array(self.acc).reshape(-1, 3, 1)
                accx = acc[:, 0, 0]
                accy = acc[:, 1, 0]
                accz = acc[:, 2, 0]

                acc_vars = [accx, accy, accz]
                for var in acc_vars:
                    min_val = np.min(var)
                    max_val = np.max(var)
                    abs_max_val = max(np.abs(max_val), np.abs(min_val))
                    self.max_acc.append(max_val)
                    self.min_acc.append(min_val)
                    self.max_acc_abs.append(abs_max_val)
                vel = -np.array(self.vel).reshape(-1, 3, 1)
                velx = vel[:, 0, 0]
                vely = vel[:, 1, 0]
                velz = vel[:, 2, 0]

                vel_vars = [velx, vely, velz]
                for var in vel_vars:
                    min_val = np.min(var)
                    max_val = np.max(var)
                    abs_max_val = max(np.abs(max_val), np.abs(min_val))
                    self.max_vel.append(max_val)
                    self.min_vel.append(min_val)
                    self.max_vel_abs.append(abs_max_val)


        elif dim==2:
            disp = -np.array(self.disp).reshape(-1, 2, 1)
            dispx = disp[:, 0, 0]
            dispy = disp[:, 1, 0]

            disp_vars = [dispx, dispy]
            for var in disp_vars:
                min_val = np.min(var)
                max_val = np.max(var)
                abs_max_val = max(np.abs(max_val),np.abs(min_val))
                self.max_disp.append(max_val)
                self.min_disp.append(min_val)
                self.max_disp_abs.append(abs_max_val)
            if self.acc:
                acc = -np.array(self.acc).reshape(-1, 2, 1)
                accx = acc[:, 0, 0]
                accy = acc[:, 1, 0]

                acc_vars = [accx, accy]
                for var in acc_vars:
                    min_val = np.min(var)
                    max_val = np.max(var)
                    abs_max_val = max(np.abs(max_val), np.abs(min_val))
                    self.max_acc.append(max_val)
                    self.min_acc.append(min_val)
                    self.max_acc_abs.append(abs_max_val)
                vel = -np.array(self.vel).reshape(-1, 2, 1)
                velx = vel[:, 0, 0]
                vely = vel[:, 1, 0]

                vel_vars = [velx, vely]
                for var in vel_vars:
                    min_val = np.min(var)
                    max_val = np.max(var)
                    abs_max_val = max(np.abs(max_val), np.abs(min_val))
                    self.max_vel.append(max_val)
                    self.min_vel.append(min_val)
                    self.max_vel_abs.append(abs_max_val)
        if self.poress is not None and len(self.poress) > 0:
            self.max_poress = max(self.poress)
            self.min_poress = min(self.poress)
            self.min_poress_abs = max(abs(self.max_poress), abs(self.min_poress))
        else:
            # 空数据时给默认值，不报错
            self.max_poress = 0.0
            self.min_poress = 0.0
            self.min_poress_abs = 0.0
    def write_Schedule(self):
        self.calc_max_min()
        dim = len(self.disp[0])
        node_output_file = f"{self.node_id}.node"
        with open(node_output_file, 'w') as node_file:
            if self.acc:
                if dim ==2:
                    node_file.write("step\taccx\taccy\tvelx\tvely\tdispx\tdispy\tpore\n")
                elif dim == 3:
                    node_file.write("step\taccx\taccy\taccz\tvelx\tvely\tvelz\tdispx\tdispy\tdispz\tpore\n")
                for step, acc, vel, disp, pore in zip(self.steps, self.acc, self.vel, self.disp, self.poress):
                    node_file.write(f"{str(step)}\t")
                    node_file.write(f"{' '.join(map(str, acc))}\t")
                    node_file.write(f"{' '.join(map(str, vel))}\t")
                    node_file.write(f"{' '.join(map(str, disp))}\t")
                    node_file.write(f"{str(pore)}\n")
            else:
                if dim == 2:
                    node_file.write("step\tdispx\tdispy\tpore\n")
                elif dim == 3:
                    node_file.write("step\tdispx\tdispy\tdispz\tpore\n")
                for step, disp, pore in zip(self.steps, self.disp, self.poress):
                    node_file.write(f"{str(step)}\t")
                    node_file.write(f"{' '.join(map(str, disp))}\t")
                    node_file.write(f"{str(pore)}\n")


    def write_step(self,step,node_file):
        if step in self.steps:
            if self.acc:
                index = self.steps.index(step)
                node_file.write(f"{str(self.node_id)}\t")
                node_file.write(f"coor\t")
                node_file.write(f"{str(self.x)}\t")
                node_file.write(f"{str(self.y)}\t")
                node_file.write(f"{str(self.z)}\t")
                node_file.write(f"{' '.join(map(str, self.disp[index]))}\t")
                node_file.write(f"{' '.join(map(str, self.vel[index]))}\t")
                node_file.write(f"{' '.join(map(str, self.acc[index]))}\t")
                node_file.write(f"{str(self.poress[index])}\n")
            else:
                index = self.steps.index(step)
                node_file.write(f"{str(self.node_id)}\t")
                node_file.write(f"coor\t")
                node_file.write(f"{str(self.x)}\t")
                node_file.write(f"{str(self.y)}\t")
                node_file.write(f"{str(self.z)}\t")
                node_file.write(f"{' '.join(map(str, self.disp[index]))}\t")
                node_file.write(f"{str(self.poress[index])}\n")


    def write_max_step(self,node_file):

        node_file.write(f"Node {self.node_id}:\t")
        node_file.write(f"coor\t")
        node_file.write(f"{str(self.x)}\t")
        node_file.write(f"{str(self.y)}\t")
        node_file.write(f"{str(self.z)}\t")
        node_file.write(f"maxdisp\t")
        node_file.write(f"{' '.join(map(str, self.max_disp))}\t")
        node_file.write(f"mindisp\t")
        node_file.write(f"{' '.join(map(str, self.min_disp))}\t")
        node_file.write(f"absmaxdisp\t")
        node_file.write(f"{' '.join(map(str, self.max_disp_abs))}\t")
        node_file.write(f"maxvel\t")
        node_file.write(f"{' '.join(map(str, self.max_vel))}\t")
        node_file.write(f"minvel\t")
        node_file.write(f"{' '.join(map(str, self.min_vel))}\t")
        node_file.write(f"absmaxvel\t")
        node_file.write(f"{' '.join(map(str, self.max_vel_abs))}\t")
        node_file.write(f"maxacc\t")
        node_file.write(f"{' '.join(map(str, self.max_acc))}\t")
        node_file.write(f"minacc\t")
        node_file.write(f"{' '.join(map(str, self.min_acc))}\t")
        node_file.write(f"absmaxacc\t")
        node_file.write(f"{' '.join(map(str, self.max_acc_abs))}\t")
        node_file.write(f"max_pore\t")
        node_file.write(f" {self.max_poress}\t")
        node_file.write(f"min_pore\t")
        node_file.write(f" {self.min_poress}\n")
        # node_file.write(f"abs_max_pore\t")
        # node_file.write(f" {self.min_poress_abs}\n")