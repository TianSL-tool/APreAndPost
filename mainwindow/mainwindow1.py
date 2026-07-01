# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
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
        self.menu.addAction(self.actionhdf5)
        self.menu.addSeparator()
        self.menu.addAction(self.actionfanyanhouchuli)
        self.menu_2.addAction(self.actionclipgrip)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionhdf5.setText(QCoreApplication.translate("MainWindow", u"hdf5\u8bfb\u53d6\u8282\u70b9\u5355\u5143", None))
        self.actionfanyanhouchuli.setText(QCoreApplication.translate("MainWindow", u"\u53cd\u6f14\u540e\u5904\u7406", None))
        self.actionclipgrip.setText(QCoreApplication.translate("MainWindow", u"\u5207\u5272\u4e09\u7ef4\u7f51\u683c", None))
        self.menu.setTitle(QCoreApplication.translate("MainWindow", u"\u540e\u5904\u7406", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindow", u"\u524d\u5904\u7406", None))
    # retranslateUi

