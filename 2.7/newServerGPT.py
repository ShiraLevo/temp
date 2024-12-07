import socket
import os
import threading
import pyautogui
import shutil
import subprocess
import traceback
import glob

# Server configuration
IP = "0.0.0.0"
PORT = 14222
MAX_PAYLOAD_SIZE = 65534

# Protocol definitions
COMMAND_CODES = {
    "TSCR": "01",
    "SNDF": "02",
    "SDIR": "03",
    "DELT": "04",
    "COPY": "05",
    "EXCT": "06",
    "EXIT": "07",
}

RESPONSE_CODES = {
    "SUCCESS": "00",
    "NOT_FOUND": "02",
    "PERMISSION_DENIED": "08",
    "ERROR": "09"
}

# Utility functions for communication
def send_with_size(data, sock):
    size = len(data).to_bytes(4, byteorder="big")
    sock.sendall(size + data)

def recv_by_size(sock):
    size = int.from_bytes(sock.recv(4), byteorder="big")
    if size == 0:
        return b""
    return sock.recv(size)

# Handling commands
def handle_screenshot(path):
    try:
        image = pyautogui.screenshot()
        image.save(path)
        return RESPONSE_CODES["SUCCESS"], f"Screenshot saved at {path}"
    except Exception as e:
        return RESPONSE_CODES["ERROR"], f"Failed to save screenshot: {e}"

def handle_directory_listing(directory_path):
    try:
        if not os.path.exists(directory_path):
            return RESPONSE_CODES["NOT_FOUND"], "Directory not found"

        files_list = glob.glob(os.path.join(directory_path, "*.*"))

        if not files_list:
            return RESPONSE_CODES["SUCCESS"], "Directory is empty"

        file_names = [os.path.basename(file) for file in files_list]
        return RESPONSE_CODES["SUCCESS"], file_names

    except Exception as e:
        return RESPONSE_CODES["ERROR"], f"Failed to read directory: {e}"

def handle_file_send(file_path, sock):
    if not os.path.isfile(file_path):
        return RESPONSE_CODES["NOT_FOUND"], "File not found"

    try:
        with open(file_path, "rb") as file:
            send_with_size(f"{RESPONSE_CODES['SUCCESS']}|Starting file transfer".encode(), sock)
            while chunk := file.read(MAX_PAYLOAD_SIZE):
                send_with_size(chunk, sock)
            send_with_size(b"", sock)
        return RESPONSE_CODES["SUCCESS"], f"File {file_path} sent successfully."
    except Exception as e:
        return RESPONSE_CODES["ERROR"], f"File sending failed: {e}"

def handle_file_delete(file_path):
    if not os.path.isfile(file_path):
        return RESPONSE_CODES["NOT_FOUND"], "File not found"
    try:
        os.remove(file_path)
        return RESPONSE_CODES["SUCCESS"], f"File {file_path} deleted"
    except PermissionError:
        return RESPONSE_CODES["PERMISSION_DENIED"], "Permission denied"
    except Exception as e:
        return RESPONSE_CODES["ERROR"], f"Failed to delete file: {e}"

def handle_file_copy(src, dst):
    try:
        shutil.copy(src, dst)
        return RESPONSE_CODES["SUCCESS"], f"File copied from {src} to {dst}"
    except Exception as e:
        return RESPONSE_CODES["ERROR"], f"Failed to copy file: {e}"

def handle_program_execution(program_path):
    try:
        subprocess.call(program_path, shell=True)
        return RESPONSE_CODES["SUCCESS"], f"Program {program_path} executed"
    except Exception as e:
        return RESPONSE_CODES["ERROR"], f"Failed to execute program: {e}"

# Handle client requests
def handle_client_request(command, params, sock):
    if command == "TSCR":
        return handle_screenshot(params)

    elif command == "SNDF":
        return handle_file_send(params, sock)

    elif command == "SDIR":
        code, file_names = handle_directory_listing(params)
        if isinstance(file_names, list):
            send_with_size(f"{code}|Directory listing starts".encode(), sock)
            for file_name in file_names:
                send_with_size(file_name.encode(), sock)
            send_with_size(b"", sock)
            return code, "Directory listing sent successfully"
        else:
            send_with_size(f"{code}|{file_names}".encode(), sock)
            return code, file_names

    elif command == "DELT":
        return handle_file_delete(params)

    elif command == "COPY":
        src, dst = params.split(" ", 1)
        return handle_file_copy(src, dst)

    elif command == "EXCT":
        return handle_program_execution(params)

    elif command == "EXIT":
        return RESPONSE_CODES["SUCCESS"], "Disconnected"

    else:
        return RESPONSE_CODES["ERROR"], "Unsupported command"

# Client handler function
def handle_client(sock, addr):
    print(f"Client {addr} connected")
    try:
        while True:
            data = recv_by_size(sock).decode()
            if not data:
                break

            command, *params = data.split("|")
            params = " ".join(params)

            code, msg = handle_client_request(command, params, sock)
            send_with_size(f"{code}|{msg}".encode(), sock)

            if command == "EXIT":
                break

    except Exception as e:
        print(f"Error handling client: {e}")
        traceback.print_exc()
    finally:
        print(f"Client {addr} disconnected")
        sock.close()

# Main server function
def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((IP, PORT))
    server_socket.listen(5)
    print("Server is running...")

    while True:
        client_sock, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_sock, addr)).start()

if __name__ == "__main__":
    main()
