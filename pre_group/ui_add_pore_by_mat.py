from PySide6.QtWidgets import QDialog
from .add_pore_by_mat import Ui_Form
from pre_group import pre

class Ui_AddPressByMat(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.init()
    def ui_AddPressByMat(self):
        Inimesh_filename = self.ui.lineEdit.text()
        control_filenname = self.ui.lineEdit_2.text()
        OutInimesh_filename = self.ui.lineEdit_3.text()
        pre.add_materials_large_scale(control_filenname,Inimesh_filename,OutInimesh_filename,10000)
        return 1

    def init(self):
        self.ui.buttonBox_2.accepted.connect(self.accept)  # OK 按钮
        self.ui.buttonBox_2.rejected.connect(self.reject)  # Cancel 按钮

