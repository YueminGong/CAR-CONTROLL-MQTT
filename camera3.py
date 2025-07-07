import subprocess
import time
import os
from picamera2 import Picamera2
from libcamera import controls

def test_imx708():
    # 初始化 Picamera2 (专为 libcamera 设计)
    picam2 = Picamera2()
    
    # 配置摄像头参数 (IMX708 推荐设置)
    config = picam2.create_still_configuration(
        main={"size": (1920, 1080)},  # IMX708 支持的分辨率
        raw={"size": picam2.sensor_resolution},
        controls={
            "AwbMode": controls.AwbModeEnum.Auto,  # 自动白平衡
            "ExposureTime": 10000,  # 曝光时间 (微秒)
            "AnalogueGain": 1.0,    # 模拟增益
        }
    )
    picam2.configure(config)
    
    # 启动摄像头
    picam2.start()
    print("IMX708 摄像头已启动 (按 Ctrl+C 退出)")

    try:
        while True:
            # 拍照测试
            filename = f"imx708_photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            picam2.capture_file(filename)
            print(f"拍照成功: {filename}")
            
            # 等待 3 秒后继续
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n用户终止测试")
    finally:
        picam2.stop()
        print("摄像头已释放")

if __name__ == "__main__":
    # 检查是否安装必要库
    try:
        test_imx708()
    except ImportError:
        print("错误：缺少依赖库，请先执行以下命令安装：")
        print("sudo apt install -y python3-picamera2 python3-libcamera")
