## 环境配置
在anaconda下用yml文件建立新的虚拟环境：
```
conda env create -f meterread_env.yml
conda activate meter_onnx
``` 
下载MMDeploy的安装包并手动安装mmdeploy_python
```
wget https://github.com/open-mmlab/mmdeploy/releases/download/v0.7.0/mmdeploy-0.7.0-linux-x86_64-onnxruntime1.8.1.tar.gz
tar -zxvf mmdeploy-0.7.0-linux-x86_64-onnxruntime1.8.1.tar.gz
cd mmdeploy-0.7.0-linux-x86_64-onnxruntime1.8.1
pip install sdk/python/mmdeploy_python-0.7.0-cp38-none-linux_x86_64.whl
```
添加onnxruntime的库：
```
wget https://github.com/microsoft/onnxruntime/releases/download/v1.8.1/onnxruntime-linux-x64-1.8.1.tgz
tar -zxvf onnxruntime-linux-x64-1.8.1.tgz
export ONNXRUNTIME_DIR=$(pwd)/onnxruntime-linux-x64-1.8.1
export LD_LIBRARY_PATH=$ONNXRUNTIME_DIR/lib:$LD_LIBRARY_PATH
```
需要注意的是，`export`只修改当前终端下的环境，如果需要修改系统设置请将相关语句加入`~/.bashrc`。

## 检测程序使用
在根目录下直接运行`main_onnx.py`可以实现对demo文件夹中图像的检测
```
python main_onnx.py
```
`main.py`中`meter_read_from_image`为检测的方法。其输入为图片位置，还有一个可选的输入为可视化结果的输出文件夹。该方法返回一个列结果表，其中列表的每一项的结构如下：
[仪表种类（Press：压力表，Wss：WSS，Temp：温度计）, 仪表位置（矩形框左上点，右下点），仪表读数（若返回-1，则说明示数读取失败）]

如果指定了可视化结果输出文件夹，则在该文件夹中保存仪表检测的可视化结果图片。

同样，可以使用`server.py`调用`main_onnx.py`中的类实现接口功能。