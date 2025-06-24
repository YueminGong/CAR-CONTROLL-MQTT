# pi_server_updated.py
# Raspberry Pi server for IP port communication
# Updated for:
# - PC IP: 192.168.106.186
# - Pi IP: 192.168.106.245

import socket
import threading
from queue import Queue

class PiCommunicationSystem:
    def __init__(self):
        # Updated network configuration
        self.pc_ip = '192.168.106.186'    # PC's new IP address
        self.recv_from_pc_port = 8080     # Port to receive data from PC (TCP)
        self.send_to_pc_port = 8800       # Port where PC listens for responses
        self.local_send_port = 8090       # Local port for sending data (UDP)
        
        # Create TCP socket for receiving data
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_socket.bind(('0.0.0.0', self.recv_from_pc_port))
        self.recv_socket.listen(5)  # Allow up to 5 queued connections
        
        # Create UDP socket for sending data
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_socket.bind(('0.0.0.0', self.local_send_port))
        
        # Data queue for received messages
        self.data_queue = Queue()
        self.running = False
        
    def start(self):
        """Start the communication system"""
        self.running = True
        print(f"Pi Communication System started")
        print(f"Listening for PC commands on port {self.recv_from_pc_port}")
        print(f"Sending responses to {self.pc_ip}:{self.send_to_pc_port}")
        
        # Start thread to handle incoming connections
        recv_thread = threading.Thread(target=self._handle_connections)
        recv_thread.daemon = True
        recv_thread.start()
        
    def stop(self):
        """Stop the communication system"""
        self.running = False
        self.recv_socket.close()
        self.send_socket.close()
        print("Communication system stopped")
        
    def _handle_connections(self):
        """Handle incoming TCP connections from PC"""
        while self.running:
            try:
                conn, addr = self.recv_socket.accept()
                print(f"Connection established from {addr}")
                
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn,)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except socket.error:
                if self.running:
                    print("Socket error occurred")
                break
    
    def _handle_client(self, conn):
        """Handle communication with a single client"""
        try:
            while self.running:
                data = conn.recv(1024)  # Receive up to 1024 bytes
                if not data:
                    break
                
                print(f"Received data: {data.hex()}")
                self.data_queue.put(data)
                
                # Process the received data
                response = self._process_data(data)
                if response:
                    self._send_response(response)
                    
        except ConnectionResetError:
            print("Client disconnected unexpectedly")
        finally:
            conn.close()
    
    def _process_data(self, data):
        """Process received data and generate response"""
        try:
            if len(data) < 1:
                return None
                
            cmd_type = data[0]  # First byte is command type
            
            # Example command processing
            if cmd_type == 0x01:  # Display control
                return self._handle_display_command(data)
            elif cmd_type == 0x02:  # Camera control
                return self._handle_camera_command(data)
            elif cmd_type == 0x03:  # LED control
                return self._handle_led_command(data)
            else:
                print(f"Unknown command type: {cmd_type:02X}")
                return bytes([0xFF, 0xFF])  # Error response
                
        except Exception as e:
            print(f"Error processing data: {str(e)}")
            return bytes([0xFF, 0xFE])  # Processing error
    
    def _handle_display_command(self, data):
        """Handle display control commands"""
        # Example implementation
        if len(data) >= 3:
            display_num = data[1]
            action = data[2]
            print(f"Display {display_num} command: {'ON' if action == 0x01 else 'OFF'}")
            return bytes([0x01, 0x00])  # Success response
        return bytes([0x01, 0xFF])  # Invalid command
    
    def _handle_camera_command(self, data):
        """Handle camera control commands"""
        # Implement camera control logic here
        return bytes([0x02, 0x00])  # Success response
    
    def _handle_led_command(self, data):
        """Handle LED strip control commands"""
        # Implement LED control logic here
        return bytes([0x03, 0x00])  # Success response
    
    def _send_response(self, data):
        """Send response data to PC via UDP"""
        try:
            self.send_socket.sendto(data, (self.pc_ip, self.send_to_pc_port))
            print(f"Sent response to {self.pc_ip}:{self.send_to_pc_port}")
        except Exception as e:
            print(f"Failed to send response: {str(e)}")

if __name__ == "__main__":
    pi_system = PiCommunicationSystem()
    try:
        pi_system.start()
        # Keep main thread alive
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        pi_system.stop()
