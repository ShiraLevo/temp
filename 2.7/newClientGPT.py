import socket
import os

# Client configuration
IP = "127.0.0.1"
PORT = 14222


# Send data with a size header
def send_with_size(data, sock):
    size = len(data).to_bytes(4, byteorder="big")
    sock.sendall(size + data.encode())


# Receive data with a size header
def recv_by_size(sock):
    size = int.from_bytes(sock.recv(4), byteorder="big")
    if size == 0:
        return b""
    return sock.recv(size)


# Save the received file locally
def save_file(file_name, data):
    with open(file_name, 'wb') as file:
        file.write(data)
    print(f"[SUCCESS] File '{file_name}' saved successfully.")


# Handle SDIR response
def handle_directory_listing(sock):
    response = recv_by_size(sock).decode()
    code, msg = response.split("|", 1)

    if code == "00" and msg == "Directory listing starts":
        print("[SUCCESS] Directory listing received:\n")
        while True:
            file_name = recv_by_size(sock).decode()
            if not file_name:
                break
            print(file_name)
    else:
        print(f"[ERROR] {msg}")


# Handle SNDF response
def request_file_from_server(sock):
    remote_file = input("Enter the file path on the server:\n").strip()
    if not remote_file:
        print("[ERROR] File path cannot be empty.")
        return

    local_file = input("Enter the file name to save locally:\n").strip()
    if not local_file:
        print("[ERROR] Local file name cannot be empty.")
        return

    send_with_size(f"SNDF|{remote_file}", sock)

    response = recv_by_size(sock).decode()
    code, msg = response.split("|", 1)

    if code == "00":
        print(f"[SUCCESS] {msg}")
        file_data = b""
        while True:
            chunk = recv_by_size(sock)
            if not chunk:
                break
            file_data += chunk
        save_file(local_file, file_data)
    else:
        print(f"[ERROR] {msg}")


# Handle file deletion
def delete_file(sock):
    file_path = input("Enter the file path to delete:\n").strip()
    if not file_path:
        print("[ERROR] File path cannot be empty.")
        return

    send_with_size(f"DELT|{file_path}", sock)
    response = recv_by_size(sock).decode()
    print(f"[SERVER RESPONSE] {response}")


# Handle file copying
def copy_file(sock):
    src = input("Enter the source file path:\n").strip()
    dst = input("Enter the destination file path:\n").strip()

    if not src or not dst:
        print("[ERROR] Source or destination path cannot be empty.")
        return

    send_with_size(f"COPY|{src} {dst}", sock)
    response = recv_by_size(sock).decode()
    print(f"[SERVER RESPONSE] {response}")


# Handle program execution
def execute_program(sock):
    program_path = input("Enter the program path to execute:\n").strip()
    if not program_path:
        print("[ERROR] Program path cannot be empty.")
        return

    send_with_size(f"EXCT|{program_path}", sock)
    response = recv_by_size(sock).decode()
    print(f"[SERVER RESPONSE] {response}")


# Main client function
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((IP, PORT))
        print("[CONNECTED] Connected to the server.")

        while True:
            print("\nAvailable Commands:")
            print("TSCR - Take Screenshot")
            print("SNDF - Download File")
            print("SDIR - Show Directory Content")
            print("DELT - Delete File")
            print("COPY - Copy File")
            print("EXCT - Execute Program")
            print("EXIT - Disconnect\n")

            command = input("Enter command:\n").strip().upper()

            if command == "TSCR":
                path = input("Enter the path to save the screenshot:\n").strip()
                send_with_size(f"{command}|{path}", sock)
                response = recv_by_size(sock).decode()
                print(f"[SERVER RESPONSE] {response}")

            elif command == "SNDF":
                request_file_from_server(sock)

            elif command == "SDIR":
                path = input("Enter the directory path:\n").strip()
                send_with_size(f"{command}|{path}", sock)
                handle_directory_listing(sock)

            elif command == "DELT":
                delete_file(sock)

            elif command == "COPY":
                copy_file(sock)

            elif command == "EXCT":
                execute_program(sock)

            elif command == "EXIT":
                send_with_size(f"{command}|", sock)
                print("[DISCONNECTING] Disconnecting from the server...")
                break

            else:
                print("[ERROR] Unsupported command. Please try again.")

    except ConnectionError:
        print("[ERROR] Failed to connect to the server.")
    finally:
        sock.close()
        print("[DISCONNECTED] Client disconnected.")


if __name__ == "__main__":
    main()
