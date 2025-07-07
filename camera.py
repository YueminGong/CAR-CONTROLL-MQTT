import cv2
import time

# 最简单的CSI摄像头测试
def test_csi_camera():
    # 初始化摄像头（0通常是CSI摄像头）
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return
    
    # 设置分辨率（可选）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("摄像头已开启，按以下键操作：")
    print("1. 按 'p' 拍照")
    print("2. 按 'v' 开始/停止录像")
    print("3. 按 'q' 退出")
    
    recording = False
    video_writer = None
    
    while True:
        # 读取摄像头画面
        ret, frame = cap.read()
        if not ret:
            print("错误：无法获取画面")
            break
        
        # 显示实时画面
        cv2.imshow('CSI Camera Test', frame)
        
        # 检测按键
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('p'):  # 拍照
            filename = f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            print(f"已保存照片: {filename}")
            
        elif key == ord('v'):  # 录像控制
            if not recording:
                # 开始录像
                filename = f"video_{time.strftime('%Y%m%d_%H%M%S')}.avi"
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
                recording = True
                print(f"开始录像: {filename}")
            else:
                # 停止录像
                video_writer.release()
                recording = False
                print("录像已停止")
                
        elif key == ord('q'):  # 退出
            break
    
    # 释放资源
    if recording:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()
    print("摄像头测试结束")

if __name__ == "__main__":
    test_csi_camera()
