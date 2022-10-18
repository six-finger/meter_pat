# -*- coding:utf-8 -*-
import cv2
import os
from datetime import datetime

from mmdeploy_python import Detector
from read_meter import split_predict_arr, cal_indication

CLASS_NAME = ("Press", "Wss", "Temp160", "Temp120")
STEP1_THRES = 0.7
STEP2_THRES = 0.6
MODEL_PATH_STEP1 = 'config_model/step1'
MODEL_PATH_STEP2 = 'config_model/step2'


class Pipe:
    def __init__(self):
        self.img = None

    def update_img(self, img):
        self.img = img

    def get_img(self):
        return self.img


class Meter:
    def __init__(self, cls_int, pos):
        self.cls_int = cls_int
        self.cls_name = CLASS_NAME[cls_int] if cls_int < 2 else "Temp"
        self.pos = pos
        self.indication = -1

    def update_indication(self, indication):
        self.indication = indication


def draw_img(raw_img, value_list):
    for meter_cls, meter_local, meter_value in value_list:

        raw_img = cv2.rectangle(raw_img,
                                (int(meter_local[0]), int(meter_local[1])),
                                (int(meter_local[2]), int(meter_local[3])),
                                (0, 0, 255), 2)
        raw_img = cv2.putText(raw_img,
                              '{}: {}'.format(meter_cls, meter_value),
                              (int(meter_local[0]), int(meter_local[1]) + 32),
                              cv2.FONT_HERSHEY_SIMPLEX,
                              fontScale=1,
                              color=(255, 0, 0),
                              thickness=2)
    return raw_img


class Meter_Read:
    def __init__(self):
        self.pipe = Pipe()
        self.pace = 0
        self.cnt = 0
        self.filenum = 0
        self.processList = []
        self.meterList = []
        self.noneList = []
        self.filenameList = []
        self.img_path = None

    def updateProcess(self, v):
        self.processList.append(v)
        print(v)

    def getProcess(self):
        return self.processList

    def updatePace(self, v):
        self.pace = v

    def getPace(self):
        return self.pace

    def updateCnt(self, v):
        self.cnt = v

    def getCnt(self):
        return self.cnt

    def updateMeterElem(self, filepath, img, cls, cnt, value):
        self.meterList.append([filepath, img, cls, cnt, value])

    def getMeterElem(self):
        return self.meterList

    def updateNoneList(self, filepath):
        self.noneList.append(filepath)

    def getNoneList(self):
        return self.noneList

    def setFilenameList(self, filename):
        self.filenameList = [v.split('/')[-1] for v in filename]

    def getFilenameList(self):
        return self.filenameList

    def setFilenum(self, num):
        self.filenum = num

    def getFilenum(self):
        return self.filenum

    def setCurrent(self, img_path):
        self.img_path = img_path

    def getCurrent(self):
        return self.img_path

    def crop_img(self, raw_img, meter):
        meter_cls, meter_local, meter_value = meter.cls_name, meter.pos, meter.indication
        xmin, ymin, xmax, ymax = int(meter_local[0]), int(meter_local[1]), int(meter_local[2]), int(meter_local[3])
        each_img = raw_img[ymin:ymax, xmin:xmax].copy()
        each_img = cv2.resize(each_img, (150, 150))
        color = (0, 255, 0) if 0.01 < float(meter_value) < 30.0 else (0, 0, 255)
        each_img = cv2.putText(each_img,
                               str(meter_value),
                               (0, 20),
                               cv2.FONT_HERSHEY_TRIPLEX,
                               fontScale=0.5,
                               color=color,
                               thickness=1)
        return each_img

    def meter_read_from_image(self, path, model_step1, model_step2, visual=None):
        self.updateProcess('\n{}'.format(path))
        img = path
        if isinstance(img, str):
            img = cv2.imread(img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.updateProcess('{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '检测全局图'))
        bboxes, labels, _ = model_step1(img)

        meter_list = []
        for idx, cls_name in enumerate(CLASS_NAME):
            detect_res = bboxes[labels == idx]
            for v in detect_res:
                if v[4] < STEP1_THRES:
                    continue
                meter_list.append(Meter(idx, v[0:4]))
        self.updatePace(self.getPace() + 5 / 10 / self.getFilenum())
        self.updateProcess('{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '检测图中每个仪表'))

        value_list = []
        raw_img = cv2.imread(path)
        for meter in meter_list:
            meter_img = img[int(meter.pos[1]):int(meter.pos[3]), int(meter.pos[0]):int(meter.pos[2])]
            bboxes, labels, _ = model_step2(meter_img)
            self.updatePace(self.getPace() + 5 / 10 / self.getFilenum() / len(meter_list))
            try:
                meter_elements = split_predict_arr(bboxes, labels, STEP2_THRES)
                meter.update_indication(cal_indication(meter_elements, meter.cls_int))
            except Exception:
                pass
            finally:
                value_list.append([meter.cls_name, meter.pos, meter.indication])
                each_img = self.crop_img(raw_img, meter)
                self.updateMeterElem(path, each_img, min(meter.cls_int, 2), self.getCnt(), meter.indication)


            # if (len(self.getFilenameList()) > 0 and self.getFilenameList()[-1] != file_name) \
            #         or len(self.getFilenameList()) == 0:
            #     self.setFilenameList(file_name)

        if len(meter_list) == 0:
            self.updateNoneList(path)

        # if visual is not None:
        #     raw_img = cv2.imread(path)
        #     res_img = draw_img(raw_img, value_list)
        #     os.makedirs(visual, exist_ok=True)
        #     cv2.imwrite(os.path.join(visual, path.split('/')[-1]), res_img)
        #     cv2.imwrite(os.path.join(visual, 'results.jpg'), res_img)

        return value_list

    def detect_from_dir(self, path):
        self.updateProcess('{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '加载模型...'))
        model1 = Detector(model_path=MODEL_PATH_STEP1, device_name='cpu', device_id=0)
        model2 = Detector(model_path=MODEL_PATH_STEP2, device_name='cpu', device_id=0)
        file_list = []
        for r, dirs, files in os.walk(path):
            for i, img_path in enumerate(files):
                if not (img_path.lower().endswith(('.bmp', '.dib', '.png', '.jpg', '.jpeg',
                                                   '.pbm', '.pgm', '.ppm', '.tif', '.tiff'))):
                    continue
                file_list.append(os.path.join(path, img_path).replace('\\', '/'))
            break
        self.setFilenum(len(file_list))
        self.updateProcess("共{}张图片".format(self.getFilenum()))
        self.setFilenameList(file_list)

        for idx, img_path in enumerate(file_list):
            self.updateCnt(idx)
            self.setCurrent(img_path)
            res = self.meter_read_from_image(img_path, model1, model2, 'res_test1_onnx')
            self.updateProcess(
                '{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ('  '.join(['{}:{}'.format(v[0], v[2]) for v in res]))))
        self.updateProcess('{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '检测完成'))
        self.updatePace(1)

    def detect_single_img(self, path):
        model1 = Detector(model_path=MODEL_PATH_STEP1, device_name='cpu', device_id=0)
        model2 = Detector(model_path=MODEL_PATH_STEP2, device_name='cpu', device_id=0)

        res = self.meter_read_from_image(path, model1, model2, 'res_test1_onnx')
        print(['{}:{}'.format(v[0].lower(), v[2]) for v in res])


