#!/usr/bin/env python3
import socket
import threading
import struct
import os
import time
from picamera2 import Picamera2
from gpiozero import LED

PC_IP = '192.168.106.186'    # PC端IP（用于白名单）
PI_IP = '192.168.106.245'    # 树莓派IP
TCP_PORT = 8080              # 指令端口
LED_GPIO = 26                # 灯带控制引脚
PHOTO_RES = (4608, 2592)     # 摄像头分辨率


class HardwareController:
    def __init__(self):

        self.light = LED(LED_GPIO)
        self.camera = Picamera2()
        self._setup_camera()
        print("inital")

    def _setup_camera(self):
        config = self.camera.create_still_configuration(
            main={"size": PHOTO_RES},
            controls={"AwbMode": 0, "ExposureTime": 20000}
        )
        self.camera.configure(config)

    def control_light(self, on):

        self.light.on() if on else self.light.off()
      
    def take_photo(self):

        filename = f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        self.camera.capture_file(filename)
        print(f"camera save: {filename}")
        return True

    def control_hdmi(self, port, on):

        cmd = f"xrandr --output HDMI-{port} {'--auto' if on else '--off'}"
        success = os.system(cmd) == 0
        status = '开启' if on else '关闭'
        print(f" HDMI-{port} {status} {'成功' if success else '失败'}")
        return success

    def cleanup(self):
        self.light.off()
        self.camera.close()


# ========== TCP ==========
class TCPServer:
    def __init__(self):
        self.controller = HardwareController()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((PI_IP, TCP_PORT))
        self.server_socket.listen(5)
        self.running = False
        print(f" 服务器启动 {PI_IP}:{TCP_PORT}")

    def start(self):

        self.running = True
        threading.Thread(target=self._accept_connections, daemon=True).start()
        print("等待客户端连接...")

    def stop(self):
        self.running = False
        self.server_socket.close()
        self.controller.cleanup()
        print("服务已停止")

    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                if addr[0] == PC_IP:
                    print(f" 客户端连接: {addr}")
                    threading.Thread(
                        target=self._handle_client,
                        args=(conn,),
                        daemon=True
                    ).start()
                else:
                    conn.close()
            except socket.error:
                if self.running: print("error")

    def _handle_client(self, conn):
        with conn:
            while self.running:
                try:
                    # 接收4字节指令 [命令类型][参数1][参数2]
                    data = conn.recv(4)
                    if not data: break

                    if len(data) != 4:
                        conn.sendall(b'\xFF\x00\x00\x00')  # 协议错误
                        continue

                    cmd, param1, param2 = struct.unpack('!BBH', data)
                    response = self._process_command(cmd, param1, param2)
                    conn.sendall(response)

                except Exception as e:
                    print(f"⚠处理指令出错: {e}")
                    break

    def _process_command(self, cmd, param1, param2):
        if cmd == 0x01:   # 灯带控制
            self.controller.control_light(bool(param1))
            return struct.pack('!BBH', 0x00, param1, 0)

        elif cmd == 0x02:  # 拍照
            success = self.controller.take_photo()
            return struct.pack('!BBH', 0x00 if success else 0xF1, 0, 0)

        elif cmd == 0x03:  # HDMI控制
            success = self.controller.control_hdmi(param1 + 1, bool(param2))
            return struct.pack('!BBH', 0x00 if success else 0xF2, param1, param2)


if __name__ == "__main__":
    server = TCPServer()
    try:
        server.start()
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n 正在停止服务...")
    finally:
        server.stop()
