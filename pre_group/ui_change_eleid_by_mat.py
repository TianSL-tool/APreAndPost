from PySide6.QtWidgets import QDialog
from .add_pore_by_mat import Ui_Form
from pre_group import pre

class Ui_ChangeEleIdByMat(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.init()
    def ui_ChangeEleIdByMat(self):
        Inimesh_filename = self.ui.lineEdit.text()
        control_filenname = self.ui.lineEdit_2.text()
        OutInimesh_filename = self.ui.lineEdit_3.text()
        pre.change_eleId_by_mat(control_filenname,Inimesh_filename,OutInimesh_filename)
        return 1

    def init(self):
        self.ui.buttonBox_2.accepted.connect(self.accept)  # OK 按钮
        self.ui.buttonBox_2.rejected.connect(self.reject)  # Cancel 按钮

