# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.9.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QMenuBar,
    QSizePolicy, QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        self.actionhdf5 = QAction(MainWindow)
        self.actionhdf5.setObjectName(u"actionhdf5")
        self.actionfanyanhouchuli = QAction(MainWindow)
        self.actionfanyanhouchuli.setObjectName(u"actionfanyanhouchuli")
        self.actionclipgrip = QAction(MainWindow)
        self.actionclipgrip.setObjectName(u"actionclipgrip")
        self.actionclipgrip.setMenuRole(QAction.MenuRole.NoRole)
        self.actionjiansuozuijindian = QAction(MainWindow)
        self.actionjiansuozuijindian.setObjectName(u"actionjiansuozuijindian")
        self.actionjiansuozuijindanyaun = QAction(MainWindow)
        self.actionjiansuozuijindanyaun.setObjectName(u"actionjiansuozuijindanyaun")
        self.actionMergeH5 = QAction(MainWindow)
        self.actionMergeH5.setObjectName(u"actionMergeH5")
        self.actionAddPressByMat = QAction(MainWindow)
        self.actionAddPressByMat.setObjectName(u"actionAddPressByMat")
        self.actionChangeEleIdByMat = QAction(MainWindow)
        self.actionChangeEleIdByMat.setObjectName(u"actionChangeEleIdByMat")
        self.actionChangeMatIdByMat = QAction(MainWindow)
        self.actionChangeMatIdByMat.setObjectName(u"actionChangeMatIdByMat")
        self.actionChangeFillIDByFill = QAction(MainWindow)
        self.actionChangeFillIDByFill.setObjectName(u"actionChangeFillIDByFill")
        self.actionChangeAllFillID = QAction(MainWindow)
        self.actionChangeAllFillID.setObjectName(u"actionChangeAllFillID")
        self.actionScaleCoorByDirection = QAction(MainWindow)
        self.actionScaleCoorByDirection.setObjectName(u"actionScaleCoorByDirection")
        self.actionExportElementsByRange = QAction(MainWindow)
        self.actionExportElementsByRange.setObjectName(u"actionExportElementsByRange")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menu = QMenu(self.menubar)
        self.menu.setObjectName(u"menu")
        self.menu_2 = QMenu(self.menubar)
        self.menu_2.setObjectName(u"menu_2")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())
        self.menu.addAction(self.actionMergeH5)
        self.menu.addAction(self.actionhdf5)
        self.menu.addSeparator()
        self.menu.addAction(self.actionfanyanhouchuli)
        self.menu_2.addAction(self.actionclipgrip)
        self.menu_2.addAction(self.actionjiansuozuijindian)
        self.menu_2.addAction(self.actionjiansuozuijindanyaun)
        self.menu_2.addSeparator()
        self.menu_2.addAction(self.actionAddPressByMat)
        self.menu_2.addAction(self.actionChangeEleIdByMat)
        self.menu_2.addAction(self.actionChangeMatIdByMat)
        self.menu_2.addAction(self.actionChangeFillIDByFill)
        self.menu_2.addAction(self.actionChangeAllFillID)
        self.menu_2.addAction(self.actionScaleCoorByDirection)
        self.menu_2.addAction(self.actionExportElementsByRange)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionhdf5.setText(QCoreApplication.translate("MainWindow", u"hdf5\u8bfb\u53d6\u8282\u70b9\u5355\u5143", None))
        self.actionfanyanhouchuli.setText(QCoreApplication.translate("MainWindow", u"\u53cd\u6f14\u540e\u5904\u7406", None))
        self.actionclipgrip.setText(QCoreApplication.translate("MainWindow", u"\u5207\u5272\u4e09\u7ef4\u7f51\u683c", None))
        self.actionjiansuozuijindian.setText(QCoreApplication.translate("MainWindow", u"\u68c0\u7d22\u6700\u8fd1\u8282\u70b9", None))
        self.actionjiansuozuijindanyaun.setText(QCoreApplication.translate("MainWindow", u"\u68c0\u7d22\u6700\u8fd1\u5355\u5143", None))
        self.actionMergeH5.setText(QCoreApplication.translate("MainWindow", u"MergeH5", None))
        self.actionAddPressByMat.setText(QCoreApplication.translate("MainWindow", u"\u6dfb\u52a0\u5b54\u538b\u7ea6\u675f_\u901a\u8fc7\u6750\u6599\u5bf9", None))
        self.actionChangeEleIdByMat.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u6539\u5355\u5143\u7c7b\u578b_\u901a\u8fc7\u7ed9\u5b9a\u6750\u6599", None))
        self.actionChangeMatIdByMat.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u6539\u6750\u6599\u53f7_\u901a\u8fc7\u6750\u6599\u53f7", None))
        self.actionChangeFillIDByFill.setText(QCoreApplication.translate("MainWindow", u"\u66f4\u6539\u586b\u7b51\u53f7_\u901a\u8fc7\u586b\u7b51\u53f7", None))
        self.actionChangeAllFillID.setText(QCoreApplication.translate("MainWindow", u"\u6240\u6709\u586b\u7b51\u53f7\u6539\u4e3a\u7edf\u4e00\u503c", None))
        self.actionScaleCoorByDirection.setText(QCoreApplication.translate("MainWindow", u"\u8282\u70b9\u7f29\u653e", None))
        self.actionExportElementsByRange.setText(QCoreApplication.translate("MainWindow", u"\u6309\u8303\u56f4\u8f93\u51fa\u5355\u5143", None))
        self.menu.setTitle(QCoreApplication.translate("MainWindow", u"\u540e\u5904\u7406", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindow", u"\u524d\u5904\u7406", None))
    # retranslateUi

