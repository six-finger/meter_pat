# -*- coding:utf-8 -*-
import os
import sys
import threading
import time
from datetime import datetime

import cv2
from PyQt5 import QtCore, QtWidgets
from PyQt5.Qt import QThread, pyqtSignal, QFileDialog, QImage, QPixmap, QLabel, QImageReader, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from qt_material import apply_stylesheet

from ui import Ui_MainWindow
from run_onnx import Meter_Read


class Embedded_Img_Table(QtWidgets.QTableWidget):
    def __init__(self):
        super().__init__()
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setColumnCount(2)
        self.setRowCount(0)
        self.horizontalHeader().setDefaultSectionSize(150)
        self.verticalHeader().setDefaultSectionSize(150)

class Worker_Infer(QThread):
    ok_signal = pyqtSignal()

    def __init__(self):
        super(Worker_Infer, self).__init__()
        self.mr = Meter_Read()
        self.path = None

    def getCnt(self):
        return self.mr.getCnt()

    def setPath(self, path):
        self.path = path

    def getPace(self):
        return self.mr.getPace()

    def getProcess(self):
        return self.mr.getProcess()

    def getMeterElem(self):
        return self.mr.getMeterElem()

    def getNoneList(self):
        return self.mr.getNoneList()

    def getCurrent(self):
        return self.mr.getCurrent()

    def getFilenameList(self):
        return self.mr.getFilenameList()

    def run(self) -> None:
        self.mr.detect_from_dir(self.path)
        self.ok_signal.emit()


class Worker_Show(QThread):
    pace_signal = pyqtSignal(int)
    text_signal = pyqtSignal(list)
    img_signal = pyqtSignal(list)
    header_signal = pyqtSignal(list)

    def __init__(self):
        super(Worker_Show, self).__init__()
        self.watched = None

    def set_watched_thread(self, th):
        self.watched = th

    def run(self) -> None:
        cnt_pace = 0
        cnt_img = 0
        while True:
            time.sleep(0.01)
            self.pace_signal.emit(int(self.watched.getPace() * 100))
            pace_lst = [v for i, v in enumerate(self.watched.getProcess()) if i >= cnt_pace]
            cnt_pace += len(pace_lst)
            self.text_signal.emit(pace_lst)
            img_lst = [v for i, v in enumerate(self.watched.getMeterElem()) if i >= cnt_img]
            cnt_img += len(img_lst)
            self.img_signal.emit(img_lst)
            self.header_signal.emit(self.watched.getFilenameList())
            if self.watched.getPace() >= 1:
                break


class Worker_Current(QThread):
    current_signal = pyqtSignal(str)
    none_signal = pyqtSignal(list)

    def __init__(self):
        super(Worker_Current, self).__init__()
        self.watched = None
        self.img = None

    def set_watched_thread(self, th):
        self.watched = th

    def run(self) -> None:
        cnt = 0
        while True:
            time.sleep(0.01)
            # if self.img != self.watched.getCurrent():
            #     self.img = self.watched.getCurrent()
            #     self.current_signal.emit(self.img)
            lst = [v for i, v in enumerate(self.watched.getNoneList()) if i >= cnt]
            cnt += len(lst)
            self.none_signal.emit(lst)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent=parent)
        self.img_dir = ''
        self.save_dir = ''
        self.cache_dict = dict()  # 记录每张图的仪表数
        self.filename_list = None

        self.setupUi(self)
        self.setWindowIcon(QIcon('icon.ico'))
        self.init_tableWidget()

        self.thread_infer = Worker_Infer()
        self.thread_infer.ok_signal.connect(lambda: self.finish_once())

        self.thread_show = Worker_Show()
        self.thread_show.set_watched_thread(self.thread_infer)
        self.thread_show.pace_signal.connect(self.change_pace)
        self.thread_show.text_signal.connect(self.change_process_list)
        self.thread_show.img_signal.connect(self.change_main_widget)
        self.thread_show.img_signal.connect(self.change_error_widget)
        self.thread_show.header_signal.connect(self.change_header_list)

        self.thread_current = Worker_Current()
        self.thread_current.set_watched_thread(self.thread_infer)
        # self.thread_current.current_signal.connect(self.change_current)
        self.thread_current.none_signal.connect(self.add_none)

        self.toolButton_2.clicked.connect(lambda: self.click_choose_dir())
        self.pushButton.clicked.connect(lambda: self.click_infer())

    def init_tableWidget(self):
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setHorizontalHeaderLabels(['现场图', '压力表', 'WSS', '温度计'])
        self.tableWidget.verticalHeader().setDefaultSectionSize(156)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        self.tableWidget_2.setColumnCount(2)
        self.tableWidget_2.setHorizontalHeaderLabels(['仪表图', '异常信息'])
        self.tableWidget_2.verticalHeader().setDefaultSectionSize(90)
        self.tableWidget_2.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget_2.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

    def change_process_list(self, lst):
        for v in lst:
            self.textBrowser.append(v)

    def change_pace(self, v):
        self.progressBar.setValue(v)

    def change_header_list(self, lst):
        self.filename_list = lst
        self.tableWidget.setVerticalHeaderLabels(lst)

    def insert_img(self, widget, path, row, size):
        reader = QImageReader()
        reader.setDecideFormatFromContent(True)
        reader.setFileName(path)
        img = reader.read()
        pic = QLabel()
        pic.setPixmap(QPixmap.fromImage(img).scaled(size, size,
                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))
        widget.setCellWidget(row, 0, pic)

    def add_none(self, lst):
        if len(lst) == 0:
            return 0
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)
        for path in lst:
            row = self.filename_list.index(path.split('/')[-1])
            if row < 0:
                return 0
            self.tableWidget.insertRow(row)
            self.insert_img(self.tableWidget, path, row, 145)

    def change_current(self, path):
        if path == '':
            return 0
        reader = QImageReader()
        reader.setDecideFormatFromContent(True)
        # reader.setScaledSize(QSize(self.label_5.width(), self.label_5.height()))
        reader.setFileName(path)
        img = reader.read()
        self.label_5.setPixmap(QPixmap.fromImage(img).scaled(self.label_5.width(), self.label_5.height(),
                                                             Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def change_main_widget(self, lst):
        for filepath, img, cls, cnt, value in lst:  # cls+1代表列，cnt代表行
            # 对图编码
            pic = QLabel()
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            img = QImage(img, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888)
            img = img.scaled(145, 145, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pic.setPixmap(QPixmap(img))
            # 获取该图的内部坐标（在子控件中的坐标）
            pos = 3 * cnt + cls
            cache_lst = self.cache_dict.get(pos, [0, None])
            v, tw = cache_lst[0], cache_lst[1]
            row_item = v // 2
            col_item = v % 2
            # 用原有子控件或创建子控件tw，并将图插入tw
            if tw is None:
                tw = Embedded_Img_Table()
            if col_item == 0:  # 若是子控件中的第0列，则为子控件新增一行从而插入
                tw.insertRow(tw.rowCount())
                if v != 0:
                    self.tableWidget.setRowHeight(cnt, self.tableWidget.rowHeight(cnt) + 156)
            tw.setCellWidget(row_item, col_item, pic)
            # 外部控件tableWidget的行数扩充
            row_count = self.tableWidget.rowCount()
            if row_count <= cnt:
                self.tableWidget.insertRow(row_count)
            # 将原图插入外部空间
            if row_item == 0 and col_item == 0:
                self.insert_img(self.tableWidget, filepath, cnt, 145)

            # 将子控件插入外部控件
            self.tableWidget.setCellWidget(cnt, cls + 1, tw)
            self.cache_dict.update({pos: [v + 1, tw]})
            # 滚动到底部
            self.tableWidget.scrollToBottom()

    def change_error_widget(self, lst):
        for filepath, img, cls, cnt, value in lst:  # cls+1代表列，cnt代表行
            if 0.01 < float(value) < 30.0:
                return
            pic = QLabel()
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            img = QImage(img, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888)
            img = img.scaled(90, 90, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pic.setPixmap(QPixmap(img))
            row_count = self.tableWidget_2.rowCount()
            self.tableWidget_2.insertRow(row_count)
            self.tableWidget_2.setCellWidget(row_count, 0, pic)

            v = QLabel()
            v.setWordWrap(True)
            str1 = filepath.split('/')[-1] + "<br />"
            str2 = ('压力表', 'Wss', '温度计')[cls] + "<br />"
            str3 = datetime.now().strftime('%m-%d %H:%M:%S') + "<br />"
            str4 = "异常示数为 {}".format(value)
            strs = "<font>" + str1 + "</font>" + \
                   "<font color = #FF0000>" + str2 + "</font>" + \
                   "<font>" + str3 + "</font>" + \
                   "<font color = #FF0000>" + str4 + "</font>"
            v.setText(strs)

            self.tableWidget_2.setCellWidget(row_count, 1, v)
            # 滚动到底部
            self.tableWidget_2.scrollToBottom()

    def click_choose_dir(self):
        img_dir = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if img_dir == "":
            return 0
        self.img_dir = img_dir
        self.save_dir = os.path.join(self.img_dir, datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        self.lineEdit.setText(self.img_dir)

    def click_infer(self):
        try:
            if self.img_dir == '':
                return 0

            self.toolButton_2.setEnabled(False)
            self.pushButton.setEnabled(False)
            _translate = QtCore.QCoreApplication.translate
            self.pushButton.setText(_translate("MainWindow", "检测中..."))

            self.init_tableWidget()

            self.cache_dict = dict()
            self.filename_list = None

            self.thread_infer.setPath(self.img_dir)
            self.thread_infer.start()
            self.thread_show.start()
            self.thread_current.start()
        except Exception as e:
            print(e)

    def finish_once(self):
        self.toolButton_2.setEnabled(True)
        self.pushButton.setEnabled(True)
        _translate = QtCore.QCoreApplication.translate
        self.pushButton.setText(_translate("MainWindow", "开始检测"))

        self.thread_infer.__init__()
        self.thread_infer.ok_signal.connect(lambda: self.finish_once())


def open_window():
    app = QtWidgets.QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    # th1 = threading.Thread(target=open_window)
    # th1.start()
    open_window()
    # pathh = r'C:/Users/mason/Pictures/test/'
    # mr = Meter_Read()
    # mr.detect_from_dir(pathh)
