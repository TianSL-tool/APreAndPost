from PySide6.QtWidgets import QDialog
from .search_node import Ui_Form
from pre_group import pre

class Ui_SearchNode(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.init()
    def ui_searchnode(self):
        print("开始检索")
        Inimesh_filename = self.ui.lineEdit.text()
        control_filenname = self.ui.lineEdit_2.text()
        pre.search_latest_node(control_filenname,Inimesh_filename)
        return 1

    def init(self):
        self.ui.buttonBox_2.accepted.connect(self.accept)  # OK 按钮
        self.ui.buttonBox_2.rejected.connect(self.reject)  # Cancel 按钮

