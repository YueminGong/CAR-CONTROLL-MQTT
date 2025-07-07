#!/usr/bin/env python3
import socket
import threading
import struct
import os
import time
import subprocess
from picamera2 import Picamera2
from gpiozero import LED


PC_IP = '192.168.106.186'    # PC端IP
PC_PORT = 8800               # PC接收端口
PI_IP = '192.168.106.245'    # 树莓派IP
TCP_PORT = 8080              # 控制端口
LED_GPIO = 26                # 灯带控制引脚
PHOTO_RES = (4608, 2592)     # 拍照分辨率
VIDEO_RES = (1920, 1080)     # 录像分辨率
DEFAULT_RECORD_TIME = 30     # 默认录像时长(秒)
AUDIO_DEVICE = "plughw:CARD=Headphones,DEV=0"
STORAGE_DIR = "/home/Documents"
PHOTO_DIR = os.path.join(STORAGE_DIR, "photo")
VIDEO_DIR = os.path.join(STORAGE_DIR, "video")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")

# ===== 指令定义 (3字节) =====
CMD_LIGHT      = 0x01  # [0x01][开/关][预留]
CMD_PHOTO      = 0x02  # [0x02][预留][预留] 
CMD_VIDEO      = 0x03  # [0x03][是否录音][时长(秒)] 
CMD_AUDIO_REC  = 0x04  # [0x04][预留][时长(秒)]
CMD_AUDIO_PLAY = 0x05  # [0x05][预留][预留]
CMD_AUDIO_STOP = 0x06  # [0x06][预留][预留]
CMD_HDMI       = 0x07  # [0x07][HDMI端口][开/关]

# ===== 硬件控制类 =====
class HardwareController:
    def __init__(self):
        self.light = LED(LED_GPIO)
        self.camera = Picamera2()
        self.audio_process = None
        self.recording = False
        self._setup_dirs()
        self._setup_camera()

    def _setup_dirs(self):
        os.makedirs(PHOTO_DIR, exist_ok=True)
        os.makedirs(VIDEO_DIR, exist_ok=True)
        os.makedirs(AUDIO_DIR, exist_ok=True)

    def _setup_camera(self):
        config = self.camera.create_still_configuration(
            main={"size": PHOTO_RES},
            controls={"AwbMode": 0, "ExposureTime": 20000}
        )
        self.camera.configure(config)

    # ----- 基础控制 -----
    def control_light(self, on):
        self.light.on() if on else self.light.off()

    def control_hdmi(self, port, on):
        cmd = f"xrandr --output HDMI-{port} {'--auto' if on else '--off'}"
        return os.system(cmd) == 0

    # ----- 媒体功能 -----
    def take_photo(self):
        filename = os.path.join(PHOTO_DIR, "latest.jpg")
        try:
            self.camera.start()
            self.camera.capture_file(filename)
            self.camera.stop()
            self._send_file(filename)
            return True
        except Exception as e:
            print(f"拍照失败: {e}")
            return False

    def start_recording(self, duration, with_audio=False):
        if self.recording: return False
        
        ext = "mp4" if with_audio else "mov"
        filename = os.path.join(VIDEO_DIR, f"latest.{ext}")
        try:
            self.recording = True
            if with_audio:
                cmd = (
                    f"ffmpeg -f v4l2 -video_size {VIDEO_RES[0]}x{VIDEO_RES[1]} "
                    f"-i /dev/video0 -f alsa -i {AUDIO_DEVICE} -t {duration} "
                    f"-c:v h264 -c:a aac {filename}"
                )
                subprocess.run(cmd, shell=True, check=True)
            else:
                video_config = self.camera.create_video_configuration(
                    main={"size": VIDEO_RES}
                )
                self.camera.switch_mode_and_capture_file(
                    video_config, 
                    filename, 
                    duration=duration
                )
            self._send_file(filename)
            return True
        except Exception as e:
            print(f"录像失败: {e}")
            return False
        finally:
            self.recording = False

    def record_audio(self, duration):
        filename = os.path.join(AUDIO_DIR, "latest.wav")
        try:
            cmd = f"arecord -D {AUDIO_DEVICE} -d {duration} -f cd {filename}"
            subprocess.run(cmd, shell=True, check=True)
            self._send_file(filename)
            return True
        except Exception as e:
            print(f"录音失败: {e}")
            return False

    def play_audio(self, filename="test.wav"):
        self.stop_audio()
        try:
            cmd = f"aplay -D {AUDIO_DEVICE} {filename}"
            self.audio_process = subprocess.Popen(cmd, shell=True)
            return True
        except Exception as e:
            print(f"播放失败: {e}")
            return False

    def stop_audio(self):
        if self.audio_process and self.audio_process.poll() is None:
            self.audio_process.terminate()
            self.audio_process.wait()
            return True
        return False

    # ----- 文件传输 -----
    def _send_file(self, filepath):
        if not os.path.exists(filepath): return False
        
        with socket.socket() as sock:
            try:
                sock.connect((PC_IP, PC_PORT))
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                
                # 发送文件头 (类型+大小)
                file_type = 0x01 if filepath.endswith('.jpg') else \
                            0x02 if filepath.endswith('.mp4') else \
                            0x03 if filepath.endswith('.wav') else 0x00
                
                sock.sendall(struct.pack('!B I', file_type, len(file_data)))
                sock.sendall(file_data)
                return True
            except Exception as e:
                print(f"文件发送失败: {e}")
                return False

    def cleanup(self):
        self.light.off()
        self.stop_audio()
        if self.recording:
            self.camera.stop_recording()
        self.camera.close()

# ===== TCP服务器 =====
class TCPServer:
    def __init__(self):
        self.controller = HardwareController()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((PI_IP, TCP_PORT))
        self.server_socket.listen(5)
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._accept_connections, daemon=True).start()
        print(f"服务已启动 {PI_IP}:{TCP_PORT}")

    # def stop(self):
    #     self.running = False
    #     self.server_socket.close()
    #     self.controller.cleanup()
    #     print("服务已停止")

    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                if addr[0] == PC_IP:
                    threading.Thread(
                        target=self._handle_client,
                        args=(conn,),
                        daemon=True
                    ).start()
                else:
                    conn.close()
            except socket.error:
                if self.running: print("接受连接出错")

    def _handle_client(self, conn):
        with conn:
            try:
                data = conn.recv(3)  # 接收3字节指令
                if len(data) != 3: return

                cmd, param1, param2 = struct.unpack('!BBB', data)
                response = self._process_command(cmd, param1, param2)
                conn.sendall(response)
            except Exception as e:
                print(f"处理指令出错: {e}")

    def _process_command(self, cmd, param1, param2):
        if cmd == CMD_LIGHT:
            self.controller.control_light(param1 == 0x01)
            return b'\x00'
        
        elif cmd == CMD_PHOTO:
            success = self.controller.take_photo()
            return b'\x00' if success else b'\xF1'
        
        elif cmd == CMD_VIDEO:
            duration = param2 if param2 > 0 else DEFAULT_RECORD_TIME
            success = self.controller.start_recording(duration, param1 == 0x01)
            return b'\x00' if success else b'\xF2'
        
        elif cmd == CMD_AUDIO_REC:
            duration = param2 if param2 > 0 else DEFAULT_RECORD_TIME
            success = self.controller.record_audio(duration)
            return b'\x00' if success else b'\xF3'
        
        elif cmd == CMD_AUDIO_PLAY:
            success = self.controller.play_audio()
            return b'\x00' if success else b'\xF4'
        
        elif cmd == CMD_AUDIO_STOP:
            success = self.controller.stop_audio()
            return b'\x00' if success else b'\xF5'
        
        elif cmd == CMD_HDMI:
            success = self.controller.control_hdmi(param1 + 1, param2 == 0x01)
            return b'\x00' if success else b'\xF6'
        
        else:
            return b'\xFE'  # 未知指令

if __name__ == "__main__":
    server = TCPServer()
    try:
        server.start()
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")
    finally:
        server.stop()
