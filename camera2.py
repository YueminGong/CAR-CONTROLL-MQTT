import cv2
import time

def test_camera():
    # CSI摄像头专用设置（树莓派官方摄像头）
    camera = cv2.VideoCapture(0)
    
    # 特别设置CSI摄像头参数
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    if not camera.isOpened():
        print("错误：摄像头无法打开")
        print("请尝试：")
        print("1. 检查摄像头连接是否牢固")
        print("2. 执行命令: sudo raspi-config 启用摄像头")
        print("3. 重启树莓派")
        return

    print("摄像头测试开始 (按Q退出)")
    print("操作提示：")
    print("- 按P拍照")
    print("- 按V开始/停止录像")

    recording = False
    video_writer = None
    
    try:
        while True:
            # 读取帧
            ret, frame = camera.read()
            if not ret:
                print("警告：获取帧失败，重试中...")
                time.sleep(0.1)
                continue
            
            # 显示画面
            cv2.imshow('Camera Test', frame)
            
            # 按键检测
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                photo_name = f"photo_{int(time.time())}.jpg"
                cv2.imwrite(photo_name, frame)
                print(f"拍照成功: {photo_name}")
            elif key == ord('v'):
                if not recording:
                    video_name = f"video_{int(time.time())}.avi"
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    video_writer = cv2.VideoWriter(video_name, fourcc, 20.0, (640, 480))
                    recording = True
                    print(f"开始录像: {video_name}")
                else:
                    video_writer.release()
                    recording = False
                    print("录像已停止")
            
            # 如果正在录像，写入帧
            if recording:
                video_writer.write(frame)
                
    finally:
        # 释放资源
        if recording:
            video_writer.release()
        camera.release()
        cv2.destroyAllWindows()
        print("摄像头测试结束")

if __name__ == "__main__":
    test_camera()
