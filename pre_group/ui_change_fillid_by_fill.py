import time

from PySide6.QtWidgets import QDialog
from .add_pore_by_mat import Ui_Form
from pre_group import pre

class Ui_ChangeFillIdByFill(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.init()
    def ui_ChangeFillIdByFill(self):
        Inimesh_filename = self.ui.lineEdit.text()
        control_filenname = self.ui.lineEdit_2.text()
        OutInimesh_filename = self.ui.lineEdit_3.text()
        self.change_fillId_by_fill(control_filenname,Inimesh_filename,OutInimesh_filename)
        return 1

    def init(self):
        self.ui.buttonBox_2.accepted.connect(self.accept)  # OK 按钮
        self.ui.buttonBox_2.rejected.connect(self.reject)  # Cancel 按钮


    def change_fillId_by_fill(self,control_filenname,Inimesh_filename,OutInimesh_filename):
        start_time = time.time()

        # 1. 先读取所有节点（节点数量通常小于单元，可一次性加载）
        nodes, elements, _, _ = pre.read_grid_file(Inimesh_filename)
        total_nodes = len(nodes)
        total_elements = len(elements)
        print(f"总节点数: {total_nodes:,}，总单元数: {total_elements:,}")

        # 6. 读取材料对信息，判断节点是否在材料对上
        class mat_pair:
            def __init__(self, oldId, newId):
                """
                初始化材料对对象

                参数:
                    mat1: 第一种材料的标识（将被转换为整数）
                    mat2: 第二种材料的标识（将被转换为整数）
                """
                try:
                    # 将输入转换为整数（处理从文件读取的字符串数据）
                    self.oldId = int(oldId)
                    self.newId = int(newId)
                except ValueError as e:
                    # 提供更明确的错误信息，便于调试
                    raise ValueError(f"材料号必须为整数，无法转换: mat1={oldId}, mat2={newId}") from e

                # 可选：添加材料号有效性验证（根据实际业务需求调整）
                if self.oldId < 0 or self.newId < 0:
                    raise ValueError(f"材料号不能为负数: mat1={self.oldId}, mat2={self.newId}")

        cleaned_lines = pre.read_and_clean_file(control_filenname)
        mat_pairs_numbers = 0
        mats = []
        mat_pairs = []

        if cleaned_lines:
            # 读取材料对数量

            mat_pairs_numbers = list(map(int, cleaned_lines.pop(0).split()))[0]
            mats = []

            for i in range(mat_pairs_numbers):
                if not cleaned_lines:
                    raise IndexError(f"文件内容不足，无法读取第{i + 1}个材料")
                line_data = cleaned_lines.pop(0).split()
                print(line_data)
                if len(line_data) != 2:
                    raise ValueError(f"材料对数据格式错误，行应为2个整数: {line_data}")

                # 使用改进后的mat_pair类
                mat_pairs.append(mat_pair(*line_data))
                mats.append(mat_pairs[-1].oldId)


            # 验证结果
            for i, pair in enumerate(mat_pairs):
                print(f"材料对 {i + 1}: type1={pair.oldId}, type2={pair.newId}")

            for i in range(len(elements)):
                if elements[i].c_id in mats:
                    for mat_pair_n in mat_pairs:
                        if elements[i].c_id == mat_pair_n.oldId:
                            elements[i].c_id = mat_pair_n.newId
                            break
            pre.write_grid_file_02(OutInimesh_filename, nodes, elements)

