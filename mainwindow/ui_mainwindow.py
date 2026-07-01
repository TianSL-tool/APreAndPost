# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.7.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QMenuBar, QMenu, QStatusBar, QDialog, QMessageBox
from PySide6.QtCore import QCoreApplication, QRect, QMetaObject
from PySide6.QtGui import QIcon, QAction

from post.postfanyan_ui import PostFanYan_UI
from post.readh5_ui import ReadH5_UI
from post.Merge_ui import MergeH5_UI
from pre_group.clip_grid_ui import Clip_Grid_UI
from pre_group.ui_search_node import Ui_SearchNode
from pre_group.ui_search_element import Ui_SearchElement
from pre_group.ui_add_pore_by_mat import Ui_AddPressByMat
from pre_group.ui_change_eleid_by_mat import Ui_ChangeEleIdByMat
from pre_group.ui_change_matid_by_mat import Ui_ChangeMatIdByMat
from pre_group.ui_change_fillid_by_fill import  Ui_ChangeFillIdByFill
from pre_group.ui_change_all_fillid import Ui_ChangeAllFillId
from pre_group.ui_scale_coor_by_direction import UiScaleCoorByDirection
from pre_group.export_elements_by_range_dialog import ExportElementsByRangeDialog
from mainwindow.mainwindow import Ui_MainWindow

# class Ui_MainWindow(object):
#     def setupUi(self, MainWindow):
#         if not MainWindow.objectName():
#             MainWindow.setObjectName(u"MainWindow")
#         MainWindow.resize(800, 600)
#         self.actionhdf5 = QAction(MainWindow)
#         self.actionhdf5.setObjectName(u"actionhdf5")
#         self.actionfanyanhouchuli = QAction(MainWindow)
#         self.actionfanyanhouchuli.setObjectName(u"actionfanyanhouchuli")
#         self.actionclipgrip = QAction(MainWindow)
#         self.actionclipgrip.setObjectName(u"actionclipgrip")
#         self.actionclipgrip.setMenuRole(QAction.MenuRole.NoRole)
#         self.actionjiansuozuijindian = QAction(MainWindow)
#         self.actionjiansuozuijindian.setObjectName(u"actionjiansuozuijindian")
#         self.actionjiansuozuijindanyaun = QAction(MainWindow)
#         self.actionjiansuozuijindanyaun.setObjectName(u"actionjiansuozuijindanyaun")
#         self.actionMergeH5 = QAction(MainWindow)
#         self.actionMergeH5.setObjectName(u"actionMergeH5")
#         self.actionAddPressByMat = QAction(MainWindow)
#         self.actionAddPressByMat.setObjectName(u"actionAddPressByMat")
#         self.actionChangeEleIdByMat = QAction(MainWindow)
#         self.actionChangeEleIdByMat.setObjectName(u"actionChangeEleIdByMat")
#         self.actionChangeMatIdByMat = QAction(MainWindow)
#         self.actionChangeMatIdByMat.setObjectName(u"actionChangeMatIdByMat")
#         self.actionChangeFillIDByFill = QAction(MainWindow)
#         self.actionChangeFillIDByFill.setObjectName(u"actionChangeFillIDByFill")
#         self.centralwidget = QWidget(MainWindow)
#         self.centralwidget.setObjectName(u"centralwidget")
#         MainWindow.setCentralWidget(self.centralwidget)
#         self.menubar = QMenuBar(MainWindow)
#         self.menubar.setObjectName(u"menubar")
#         self.menubar.setGeometry(QRect(0, 0, 800, 33))
#         self.menu = QMenu(self.menubar)
#         self.menu.setObjectName(u"menu")
#         self.menu_2 = QMenu(self.menubar)
#         self.menu_2.setObjectName(u"menu_2")
#         MainWindow.setMenuBar(self.menubar)
#         self.statusbar = QStatusBar(MainWindow)
#         self.statusbar.setObjectName(u"statusbar")
#         MainWindow.setStatusBar(self.statusbar)
#
#         self.menubar.addAction(self.menu.menuAction())
#         self.menubar.addAction(self.menu_2.menuAction())
#         self.menu.addAction(self.actionMergeH5)
#         self.menu.addAction(self.actionhdf5)
#         self.menu.addSeparator()
#         self.menu.addAction(self.actionfanyanhouchuli)
#         self.menu_2.addAction(self.actionclipgrip)
#         self.menu_2.addAction(self.actionjiansuozuijindian)
#         self.menu_2.addAction(self.actionjiansuozuijindanyaun)
#         self.menu_2.addSeparator()
#         self.menu_2.addAction(self.actionAddPressByMat)
#         self.menu_2.addAction(self.actionChangeEleIdByMat)
#         self.menu_2.addAction(self.actionChangeMatIdByMat)
#         self.menu_2.addAction(self.actionChangeFillIDByFill)
#
#         self.retranslateUi(MainWindow)
#
#         QMetaObject.connectSlotsByName(MainWindow)
#     # setupUi
#
#     def retranslateUi(self, MainWindow):
#         MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
#         self.actionhdf5.setText(QCoreApplication.translate("MainWindow", u"hdf5\u8bfb\u53d6\u8282\u70b9\u5355\u5143", None))
#         self.actionfanyanhouchuli.setText(QCoreApplication.translate("MainWindow", u"\u53cd\u6f14\u540e\u5904\u7406", None))
#         self.actionclipgrip.setText(QCoreApplication.translate("MainWindow", u"\u5207\u5272\u4e09\u7ef4\u7f51\u683c", None))
#         self.actionjiansuozuijindian.setText(QCoreApplication.translate("MainWindow", u"\u68c0\u7d22\u6700\u8fd1\u8282\u70b9", None))
#         self.actionjiansuozuijindanyaun.setText(QCoreApplication.translate("MainWindow", u"\u68c0\u7d22\u6700\u8fd1\u5355\u5143", None))
#         self.actionMergeH5.setText(QCoreApplication.translate("MainWindow", u"MergeH5", None))
#         self.actionAddPressByMat.setText(QCoreApplication.translate("MainWindow", u"\u6dfb\u52a0\u5b54\u538b\u7ea6\u675f_\u901a\u8fc7\u6750\u6599\u5bf9", None))
#         self.actionChangeEleIdByMat.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u6539\u5355\u5143\u7c7b\u578b_\u901a\u8fc7\u7ed9\u5b9a\u6750\u6599", None))
#         self.actionChangeMatIdByMat.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u6539\u6750\u6599\u53f7_\u901a\u8fc7\u6750\u6599\u53f7", None))
#         self.actionChangeFillIDByFill.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u6539\u586b\u7b51\u53f7_\u901a\u8fc7\u586b\u7b51\u53f7", None))
#         self.menu.setTitle(QCoreApplication.translate("MainWindow", u"\u540e\u5904\u7406", None))
#         self.menu_2.setTitle(QCoreApplication.translate("MainWindow", u"\u524d\u5904\u7406", None))
#     # retranslateUi

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init()


    def init(self):
        self.actionMergeH5.triggered.connect(self.openMergeH5Dialog)
        self.actionhdf5.triggered.connect(self.openReadH5Dialog)
        self.actionfanyanhouchuli.triggered.connect(self.openPostFanYanDialog)
        self.actionclipgrip.triggered.connect(self.openClipGridDialog)
        self.actionjiansuozuijindian.triggered.connect(self.open_search_latest_node_Dialog)
        self.actionjiansuozuijindanyaun.triggered.connect(self.open_search_latest_element_Dialog)
        self.actionAddPressByMat.triggered.connect(self.openAddPressByMat)
        self.actionChangeEleIdByMat.triggered.connect(self.openChangeEleIdByMat)
        self.actionChangeMatIdByMat.triggered.connect(self.openChangeMatIdByMat)
        self.actionChangeFillIDByFill.triggered.connect(self.openChangeFillIdByFill)
        self.actionChangeAllFillID.triggered.connect(self.openChangeAllFillId)
        self.actionScaleCoorByDirection.triggered.connect(self.openScaleCoorByDirection)
        self.actionExportElementsByRange.triggered.connect(self.openExportElementsByRange)
    def openReadH5Dialog(self):
        # 创建并显示设置弹窗
        dialog = ReadH5_UI()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数
                parameters = dialog.ui_readh5()

                if parameters ==1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break


    def openPostFanYanDialog(self):
        # 创建并显示设置弹窗
        dialog = PostFanYan_UI()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数
                parameters = dialog.ui_postfanyan()

                if parameters ==1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break



    def openClipGridDialog(self):
        # 创建并显示设置弹窗
        dialog = Clip_Grid_UI()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数
                parameters = dialog.ui_clip_grid()

                if parameters ==1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break


    def open_search_latest_element_Dialog(self):
        # 创建并显示设置弹窗
        dialog = Ui_SearchElement()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数
                parameters = dialog.ui_searchelement()

                if parameters ==1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break

    def open_search_latest_node_Dialog(self):

        # 创建并显示设置弹窗
        dialog = Ui_SearchNode()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数
                print(111)
                parameters = dialog.ui_searchnode()

                if parameters ==1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break
    def openMergeH5Dialog(self):
        dialog = MergeH5_UI()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数

                parameters = dialog.MergeH5()

                if parameters == 1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break

    def openAddPressByMat(self):
        dialog = Ui_AddPressByMat()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数

                parameters = dialog.ui_AddPressByMat()

                if parameters == 1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break

    def openChangeEleIdByMat(self):
        dialog = Ui_ChangeEleIdByMat()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数

                parameters = dialog.ui_ChangeEleIdByMat()

                if parameters == 1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break


    def openChangeMatIdByMat(self):
        dialog = Ui_ChangeMatIdByMat()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数

                parameters = dialog.ui_ChangeMatIdByMat()

                if parameters == 1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break
    def openChangeFillIdByFill(self):
        dialog = Ui_ChangeFillIdByFill()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数

                parameters = dialog.ui_ChangeFillIdByFill()

                if parameters == 1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break
    def openChangeAllFillId(self):
        dialog = Ui_ChangeAllFillId()
        while True:
            if dialog.exec() == QDialog.Accepted:
                if dialog.ui_change_all_fill_id() == 1:
                    break
            else:
                break
    def openScaleCoorByDirection(self):
        dialog = UiScaleCoorByDirection()

        # 循环检查参数，确保不退出
        while True:
            if dialog.exec() == QDialog.Accepted:
                # 获取设置参数

                parameters = dialog.ui_scale_coor_by_direction()

                if parameters == 1:
                    QMessageBox.information(dialog, "计算完成", f"计算完成")
                    break  # 退出循环，关闭对话框
                else:
                    # 参数为空，继续停留在设置弹窗
                    QMessageBox.warning(dialog, "参数错误", "计算失败！")
            else:
                # 如果用户点击取消，则退出
                break

    def openExportElementsByRange(self):
        dialog = ExportElementsByRangeDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.export_result:
            node_count, element_count, output_filename = dialog.export_result
            QMessageBox.information(
                self,
                "输出完成",
                f"已输出 {element_count} 个单元、{node_count} 个引用节点。\n"
                f"输出文件：{output_filename}",
            )
