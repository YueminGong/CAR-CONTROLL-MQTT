#!/usr/bin/env python3
from picamera2 import Picamera2
import time
import os

def setup_camera():
    """配置IMX708摄像头参数"""
    picam2 = Picamera2()
    
    # IMX708推荐配置（根据实际需求调整）
    config = picam2.create_still_configuration(
        main={"size": (4608, 2592)},  # 4K分辨率
        raw={"size": picam2.sensor_resolution},
        controls={
            "AwbMode": 0,            # 0=自动白平衡
            "ExposureTime": 20000,    # 20ms曝光
            "AnalogueGain": 1.5,      # 模拟增益
            "FrameRate": 30.0,        # 帧率
        }
    )
    picam2.configure(config)
    return picam2

def capture_photo(picam2, filename=None):
    """拍照测试"""
    if filename is None:
        filename = f"IMX708_photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    picam2.capture_file(filename)
    print(f"✅ 照片已保存: {os.path.abspath(filename)}")

def record_video(picam2, duration=10, filename=None):
    """录像测试"""
    if filename is None:
        filename = f"IMX708_video_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
    
    # 需要先切换到视频配置
    video_config = picam2.create_video_configuration(
        main={"size": (1920, 1080)},  # 1080p录像
        controls={"FrameRate": 30}
    )
    picam2.switch_mode_and_capture_file(video_config, filename, duration=duration)
    print(f"✅ 视频已保存: {os.path.abspath(filename)}")

def live_preview(picam2, duration=10):
    """实时预览测试"""
    picam2.start_preview()
    picam2.start()
    print(f"🔍 实时预览中 (持续{duration}秒，按Ctrl+C退出)...")
    time.sleep(duration)
    picam2.stop_preview()
    picam2.stop()

def main():
    picam2 = setup_camera()
    
    try:
        print("\nIMX708 测试菜单:")
        print("1. 实时预览 (10秒)")
        print("2. 拍摄照片")
        print("3. 录制视频 (10秒)")
        print("4. 退出")
        
        choice = input("请选择测试项目 [1-4]: ")
        
        if choice == "1":
            live_preview(picam2)
        elif choice == "2":
            capture_photo(picam2)
        elif choice == "3":
            record_video(picam2)
        elif choice == "4":
            return
        else:
            print("无效输入！")
            
    finally:
        picam2.close()
        print("摄像头资源已释放")

if __name__ == "__main__":
    # 检查是否是树莓派环境
    if not os.path.exists("/dev/video0"):
        print("错误：未检测到摄像头设备！")
        print("请执行以下步骤检查：")
        print("1. 确认摄像头已物理连接")
        print("2. 执行命令: sudo raspi-config → Interface Options → Camera → 启用")
        print("3. 重启树莓派")
        exit(1)
        
    main()
