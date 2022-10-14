# -*- coding:utf-8 -*-
import os
import sys
import threading
import time
from datetime import datetime

import cv2
from PyQt5 import QtCore, QtWidgets
from PyQt5.Qt import QThread, pyqtSignal, QFileDialog, QImage, QPixmap, QLabel, QImageReader, QSize
from PyQt5.QtCore import Qt

from ui import Ui_MainWindow
from run_onnx import Meter_Read


class Embedded_Table(QtWidgets.QTableWidget):
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

    def setPath(self, path):
        self.path = path

    def getPace(self):
        return self.mr.getPace()

    def getProcess(self):
        return self.mr.getProcess()

    def getMeter(self):
        return self.mr.getMeter()

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
            img_lst = [v for i, v in enumerate(self.watched.getMeter()) if i >= cnt_img]
            cnt_img += len(img_lst)
            self.img_signal.emit(img_lst)
            self.header_signal.emit(self.watched.getFilenameList())
            if self.watched.getPace() >= 1:
                break


class Worker_Current(QThread):
    current_signal = pyqtSignal(str)

    def __init__(self):
        super(Worker_Current, self).__init__()
        self.watched = None
        self.img = None

    def set_watched_thread(self, th):
        self.watched = th

    def run(self) -> None:
        while True:
            time.sleep(0.01)
            if self.img != self.watched.getCurrent():
                self.img = self.watched.getCurrent()
                self.current_signal.emit(self.img)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent=parent)
        self.img_dir = ''
        self.save_dir = ''
        self.cache_dict = dict()   # 记录每张图的仪表数

        self.setupUi(self)

        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['压力表', 'Wss', '温度计'])
        self.tableWidget.verticalHeader().setDefaultSectionSize(152)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(308)

        self.thread_infer = Worker_Infer()
        self.thread_infer.ok_signal.connect(lambda: self.set_btn())

        self.thread_show = Worker_Show()
        self.thread_show.set_watched_thread(self.thread_infer)
        self.thread_show.pace_signal.connect(self.change_pace)
        self.thread_show.text_signal.connect(self.change_process_list)
        self.thread_show.img_signal.connect(self.change_meter_list)
        self.thread_show.header_signal.connect(self.change_header_list)

        self.thread_current = Worker_Current()
        self.thread_current.set_watched_thread(self.thread_infer)
        self.thread_current.current_signal.connect(self.change_current)

        self.toolButton_2.clicked.connect(lambda: self.click_choose_dir())
        self.pushButton.clicked.connect(lambda: self.click_infer())

    def change_process_list(self, lst):
        for v in lst:
            self.textBrowser.append(v)

    def change_pace(self, v):
        self.progressBar.setValue(v)

    def change_header_list(self, lst):
        self.tableWidget.setVerticalHeaderLabels(lst)

    def change_current(self, path):
        if path == '':
            return 0
        # img = cv2.imread(path)
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # img = QImage(img, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888)  # 参数依次为：图像、宽、高、每一行的字节数、图像格式彩色图像一般为Format_RGB888
        # img = img.scaled(self.label_5.width(), self.label_5.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # img = QPixmap(img)        # QImage类型图像放入QPixmap
        # self.label_5.setPixmap(img)    # 显示在label中

        # image = QImage(path)
        # image.scaled(self.label_5.width(), self.label_5.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # self.label_5.setPixmap(QPixmap.fromImage(image))

        reader = QImageReader()
        reader.setDecideFormatFromContent(True)
        reader.setScaledSize(QSize(self.label_5.width(), self.label_5.height()))
        reader.setFileName(path)
        img = reader.read()
        self.label_5.setPixmap(QPixmap.fromImage(img))


    def change_meter_list(self, lst):
        for file_name, img, cls, cnt in lst:   # cls代表列，cnt代表行
            # 对图编码
            pic = QLabel()
            img = QImage(img, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888)
            img = img.scaled(150, 150, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pic.setPixmap(QPixmap(img))
            # 获取该图的内部坐标（在子控件中的坐标）
            pos = 3 * cnt + cls
            lst = self.cache_dict.get(pos, [0, None])
            v, tw = lst[0], lst[1]
            row_item = v // 2
            col_item = v % 2
            # 用原有子控件或创建子控件tw，并将图插入tw
            if tw is None:
                tw = Embedded_Table()
            if col_item == 0:   # 若当前是子控件中的第0列，则为子控件新增一行从而插入
                tw.insertRow(tw.rowCount())
                if v != 0:
                    self.tableWidget.setRowHeight(cnt, self.tableWidget.rowHeight(cnt)+153)

            tw.setCellWidget(row_item, col_item, pic)
            # 外部控件tableWidget的行数扩充
            row_count = self.tableWidget.rowCount()
            if row_count <= cnt:
                self.tableWidget.insertRow(row_count)
            # 将子控件插入外部控件
            self.tableWidget.setCellWidget(cnt, cls, tw)
            self.cache_dict.update({pos: [v + 1, tw]})
            # 滚动到底部
            self.tableWidget.scrollToBottom()

    def click_choose_dir(self):
        img_dir = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if img_dir == "":
            return 0
        self.img_dir = img_dir
        self.save_dir = os.path.join(self.img_dir, datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        self.lineEdit.setText(self.img_dir)

    def click_infer(self):
        if self.img_dir == '':
            return 0

        self.toolButton_2.setEnabled(False)
        self.pushButton.setEnabled(False)

        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(['压力表', 'Wss', '温度计'])
        self.tableWidget.verticalHeader().setDefaultSectionSize(152)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(308)

        _translate = QtCore.QCoreApplication.translate
        self.pushButton.setText(_translate("MainWindow", "检测中..."))

        self.cache_dict = dict()
        self.tableWidget.clearContents()
        self.tableWidget.clearSelection()
        self.thread_infer.setPath(self.img_dir)
        self.thread_infer.start()

        self.thread_show.start()
        self.thread_current.start()

    def set_btn(self):
        self.toolButton_2.setEnabled(True)
        self.pushButton.setEnabled(True)
        _translate = QtCore.QCoreApplication.translate
        self.pushButton.setText(_translate("MainWindow", "开始检测"))



def open_window():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    th1 = threading.Thread(target=open_window)
    th1.start()
    # pathh = r'C:/Users/mason/Pictures/test/'
    # mr = Meter_Read()
    # mr.detect_from_dir(pathh)
