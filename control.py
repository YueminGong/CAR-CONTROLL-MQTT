import serial
import time
import json
import paho.mqtt.client as mqtt
import threading

# ????
UPLOAD_DATA = 1
MOTOR_TYPE = 1
MQTT_BROKER = "21.tcp.vip.cpolar.cn"
MQTT_PORT = 13234
MQTT_TOPIC = "unity_car_tracking/controller"

# ?????
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

# ????
recv_buffer = ""
current_speeds = [0, 0, 0, 0]  # ?????? [M1, M2, M3, M4]
mqtt_client = None
last_command_time = 0
command_active = False

# ??????
def send_data(data):
    ser.write(data.encode())
    time.sleep(0.01)

def receive_data():
    global recv_buffer
    if ser.in_waiting > 0:
        recv_buffer += ser.read(ser.in_waiting).decode()
        messages = recv_buffer.split("#")
        recv_buffer = messages[-1]
        if len(messages) > 1:
            return messages[0] + "#"
    return None

# ??????
def control_speed(m1, m2, m3, m4):
    send_data("$spd:{},{},{},{}#".format(m1, m2, m3, m4))

def control_pwm(m1, m2, m3, m4):
    send_data("$pwm:{},{},{},{}#".format(m1, m2, m3, m4))

def send_upload_command(mode):
    if mode == 0:
        send_data("$upload:0,0,0#")
    elif mode == 1:
        send_data("$upload:1,0,0#")
    elif mode == 2:
        send_data("$upload:0,1,0#")
    elif mode == 3:
        send_data("$upload:0,0,1#")

# ??????
def set_motor_type(data):
    send_data("$mtype:{}#".format(data))

def set_motor_deadzone(data):
    send_data("$deadzone:{}#".format(data))

def set_pluse_line(data):
    send_data("$mline:{}#".format(data))

def set_pluse_phase(data):
    send_data("$mphase:{}#".format(data))

def set_wheel_dis(data):
    send_data("$wdiameter:{}#".format(data))

def set_motor_parameter():
    if MOTOR_TYPE == 1:
        set_motor_type(1)
        set_pluse_phase(30)
        set_pluse_line(11)
        set_wheel_dis(67.00)
        set_motor_deadzone(1600)
    elif MOTOR_TYPE == 2:
        set_motor_type(2)
        set_pluse_phase(20)
        set_pluse_line(13)
        set_wheel_dis(48.00)
        set_motor_deadzone(1300)
    elif MOTOR_TYPE == 3:
        set_motor_type(3)
        set_pluse_phase(45)
        set_pluse_line(13)
        set_wheel_dis(68.00)
        set_motor_deadzone(1250)
    elif MOTOR_TYPE == 4:
        set_motor_type(4)
        set_pluse_phase(48)
        set_motor_deadzone(1000)
    elif MOTOR_TYPE == 5:
        set_motor_type(1)
        set_pluse_phase(40)
        set_pluse_line(11)
        set_wheel_dis(67.00)
        set_motor_deadzone(1600)
    time.sleep(0.5)

# ??????
def parse_data(data):
    data = data.strip()
    if data.startswith("$MAll:"):
        values_str = data[6:-1]
        values = list(map(int, values_str.split(',')))
        return '????: ' + ', '.join([f"M{i+1}:{value}" for i, value in enumerate(values)])
    elif data.startswith("$MTEP:"):
        values_str = data[6:-1]
        values = list(map(int, values_str.split(',')))
        return '?????: ' + ', '.join([f"M{i+1}:{value}" for i, value in enumerate(values)])
    elif data.startswith("$MSPD:"):
        values_str = data[6:-1]
        values = [float(value) if '.' in value else int(value) for value in values_str.split(',')]
        return '????: ' + ', '.join([f"M{i+1}:{value}mm/s" for i, value in enumerate(values)])
    return None

# MQTT????
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"?????MQTT???: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"?????: {MQTT_TOPIC}")
    else:
        print(f"????,????: {rc}")

def on_message(client, userdata, msg):
    global current_speeds, last_command_time, command_active
    
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        power = int(data.get('power', 0))  # ????
        move_speed = float(data.get('movespeed', 0))  # ????0
        move_x = float(data.get('movex', 1.0))  # ????
        
        print(f"?????? - ??: {power}, ??: {move_speed}, ??: {move_x}")
        
        if power == 1:  # ???power=1????
            # ???? (movespeed*200 ???movex???)
            speed = int(move_speed * 200) * (1 if move_x >= 0 else -1)
            
            # ??????????
            current_speeds = [speed, speed, speed, speed]
            
            # ?????????
            last_command_time = time.time()
            command_active = True
            
            print(f"????,??: {current_speeds}")
        else:
            # power?1?????
            current_speeds = [0, 0, 0, 0]
            command_active = False
            print("????")
            
    except Exception as e:
        print(f"??MQTT????: {str(e)}")

# ???MQTT???
def init_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        print(f"?????MQTT???: {MQTT_BROKER}:{MQTT_PORT}...")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        return True
    except Exception as e:
        print(f"MQTT????: {str(e)}")
        return False

# ?????
def control_loop():
    global current_speeds, command_active, last_command_time
    
    print("?????...")
    send_upload_command(UPLOAD_DATA)
    set_motor_parameter()
    
    try:
        while True:
            # ??????
            received_message = receive_data()
            if received_message:
                parsed = parse_data(received_message)
                if parsed:
                    print(parsed)
            
            # ??????1?????
            if command_active and (time.time() - last_command_time) >= 1.0:
                current_speeds = [0, 0, 0, 0]
                command_active = False
                print("1????,????")
            
            # ??????
            if MOTOR_TYPE == 4:
                control_pwm(*[s*2 for s in current_speeds])
            else:
                control_speed(*current_speeds)
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n????...")
    finally:
        # ??????
        if MOTOR_TYPE == 4:
            control_pwm(0, 0, 0, 0)
        else:
            control_speed(0, 0, 0, 0)
        print("???????")

if __name__ == "__main__":
    # ??MQTT???
    if not init_mqtt():
        print("MQTT?????,????")
        exit(1)
    
    # ??????
    control_loop()
    
    # ??
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    ser.close()
    print("?????")
