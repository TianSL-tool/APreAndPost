# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'clip_grid_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)

from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialogButtonBox, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
                               QSpacerItem, QVBoxLayout, QWidget, QDialog)
from pre_group import pre
class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(299, 171)
        self.horizontalLayout = QHBoxLayout(Form)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.widget = QWidget(Form)
        self.widget.setObjectName(u"widget")
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lineEdit = QLineEdit(self.widget)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout.addWidget(self.lineEdit, 0, 1, 1, 1)

        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.lineEdit_3 = QLineEdit(self.widget)
        self.lineEdit_3.setObjectName(u"lineEdit_3")

        self.gridLayout.addWidget(self.lineEdit_3, 2, 1, 1, 1)

        self.lineEdit_2 = QLineEdit(self.widget)
        self.lineEdit_2.setObjectName(u"lineEdit_2")

        self.gridLayout.addWidget(self.lineEdit_2, 1, 1, 1, 1)

        self.label = QLabel(self.widget)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_4 = QLabel(self.widget)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.lineEdit_4 = QLineEdit(self.widget)
        self.lineEdit_4.setObjectName(u"lineEdit_4")

        self.gridLayout.addWidget(self.lineEdit_4, 3, 1, 1, 1)


        self.verticalLayout.addWidget(self.widget)

        self.buttonBox_2 = QDialogButtonBox(Form)
        self.buttonBox_2.setObjectName(u"buttonBox_2")
        self.buttonBox_2.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.buttonBox_2.setCenterButtons(True)

        self.verticalLayout.addWidget(self.buttonBox_2)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_3)


        self.horizontalLayout.addLayout(self.verticalLayout)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.lineEdit.setText(QCoreApplication.translate("Form", u"Inimesh.dat", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"\u8f93\u51fa\u6587\u4ef6\uff1a", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"\u5207\u5272\u9762\u4fe1\u606f\u6587\u4ef6\uff1a", None))
        self.lineEdit_3.setText(QCoreApplication.translate("Form", u"output.dat", None))
        self.lineEdit_2.setText(QCoreApplication.translate("Form", u"control.dat", None))
        self.label.setText(QCoreApplication.translate("Form", u"\u7f51\u683c\u6587\u4ef6\uff1a", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"\u63a7\u5236\u5408\u5e76\u5bb9\u5dee\uff1a", None))
        self.lineEdit_4.setText(QCoreApplication.translate("Form", u"1.0e-4", None))
    # retranslateUi

SOFTWARE_NAME = "三维切割软件"
class Clip_Grid_UI(QDialog, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init()
        self.setWindowTitle(f"{SOFTWARE_NAME} ")

    def ui_clip_grid(self):
        Inimesh_filename1 = self.lineEdit.text()
        control_filenname = self.lineEdit_2.text()
        output_filenname = self.lineEdit_3.text()
        tol = float(self.lineEdit_4.text())
        pre.clip_inimesh(Inimesh_filename1,control_filenname,output_filenname,tol)
        return 1

    def init(self):
        self.buttonBox_2.accepted.connect(self.accept)  # OK 按钮
        self.buttonBox_2.rejected.connect(self.reject)  # Cancel 按钮

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = PostFanYan_UI()
#     window.show()
#     sys.exit(app.exec())
