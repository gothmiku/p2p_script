import socket
import ssl
import threading
import os
import json

# Load configuration from JSON
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

config = load_config()

PORT = config["port"]
SHARED_FOLDER = config["shared_folder"]
DOWNLOAD_FOLDER = config["download_folder"]
CERT_FILE = config["cert_file"]
KEY_FILE = config["key_file"]

# Secure context for server
def create_ssl_context_server():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    return context

# Secure context for client
def create_ssl_context_client():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # disable verification for self-signed certs
    return context

# Server thread
def peer_server():
    context = create_ssl_context_server()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", PORT))
    sock.listen(5)
    print(f"[SERVER] Listening on port {PORT} (TLS enabled)...")

    while True:
        conn, addr = sock.accept()
        secure_conn = context.wrap_socket(conn, server_side=True)
        threading.Thread(target=handle_client, args=(secure_conn, addr)).start()

def handle_client(conn, addr):
    print(f"[SERVER] Secure connection from {addr}")
    try:
        conn.sendall(b"Welcome to the peer. Options:\n1. LIST\n2. DOWNLOAD <filename>\n3. UPLOAD <filename>\nEnter command: ")

        while True:
            command = conn.recv(1024).decode().strip()
            if not command:
                break

            if command.upper() == "LIST":
                files = os.listdir(SHARED_FOLDER)
                file_list = "\n".join(files) or "[empty]"
                conn.sendall(file_list.encode())

            elif command.upper().startswith("DOWNLOAD "):
                filename = command[9:].strip()
                filepath = os.path.join(SHARED_FOLDER, filename)

                if os.path.exists(filepath):
                    conn.sendall(b"FOUND")
                    with open(filepath, "rb") as f:
                        while True:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            conn.sendall(chunk)
                    print(f"[SERVER] Sent: {filename} to {addr}")
                else:
                    conn.sendall(b"NOT_FOUND")

            elif command.upper().startswith("UPLOAD "):
                filename = command[7:].strip()
                save_path = os.path.join(SHARED_FOLDER, filename)

                conn.sendall(b"READY")  # signal client to start upload
                with open(save_path, "wb") as f:
                    while True:
                        data = conn.recv(4096)
                        if not data:
                            break
                        f.write(data)
                print(f"[SERVER] Received upload: {filename} from {addr}")
                conn.sendall(b"UPLOAD_COMPLETE")
                break

            else:
                conn.sendall(b"Invalid command.\n")
    except Exception as e:
        print(f"[SERVER] Error: {e}")
    finally:
        conn.close()

# Client
def peer_client(peer_ip):
    context = create_ssl_context_client()
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    secure_sock = context.wrap_socket(raw_sock, server_hostname=peer_ip)

    try:
        secure_sock.connect((peer_ip, PORT))
        print(f"[CLIENT] Connected securely to {peer_ip}:{PORT}")

        welcome_msg = secure_sock.recv(4096).decode()
        print(welcome_msg)

        while True:
            cmd = input("[CLIENT] Enter command (LIST, DOWNLOAD <filename>, UPLOAD <filename>, EXIT): ").strip()
            if cmd.upper() == "EXIT":
                break

            secure_sock.sendall(cmd.encode())

            if cmd.upper() == "LIST":
                file_list = secure_sock.recv(8192).decode()
                print("[CLIENT] Peer’s shared files:\n" + file_list)

            elif cmd.upper().startswith("DOWNLOAD "):
                status = secure_sock.recv(1024).decode()
                if status == "FOUND":
                    filename = cmd[9:].strip()
                    if not os.path.exists(DOWNLOAD_FOLDER):
                        os.makedirs(DOWNLOAD_FOLDER)
                    save_path = os.path.join(DOWNLOAD_FOLDER, filename)
                    print(f"[CLIENT] Downloading {filename}...")
                    with open(save_path, "wb") as f:
                        while True:
                            data = secure_sock.recv(4096)
                            if not data:
                                break
                            f.write(data)
                    print(f"[CLIENT] Downloaded {filename} successfully.")
                else:
                    print("[CLIENT] File not found on peer.")

            elif cmd.upper().startswith("UPLOAD "):
                filename = cmd[7:].strip()
                file_path = os.path.join(SHARED_FOLDER, filename)
                if not os.path.exists(file_path):
                    print("[CLIENT] File not found in your shared folder.")
                    continue

                response = secure_sock.recv(1024).decode()
                if response == "READY":
                    print(f"[CLIENT] Uploading {filename}...")
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            secure_sock.sendall(chunk)
                    print(f"[CLIENT] Uploaded {filename} successfully.")
                    # wait for confirmation
                    confirm = secure_sock.recv(1024).decode()
                    if confirm == "UPLOAD_COMPLETE":
                        print("[CLIENT] Upload confirmed by peer.")

            else:
                response = secure_sock.recv(1024).decode()
                print(f"[CLIENT] {response}")

    except Exception as e:
        print(f"[CLIENT] Error: {e}")
    finally:
        secure_sock.close()

def main():
    if not os.path.exists(SHARED_FOLDER):# create folders if they don’t exist
        os.makedirs(SHARED_FOLDER)
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    print("=== Encrypted P2P Folder Sharing (Configurable) ===")
    print(f"Your shared folder: {SHARED_FOLDER}/")
    print(f"Your download folder: {DOWNLOAD_FOLDER}/")
    print(f"Listening on port: {PORT}")

    threading.Thread(target=peer_server, daemon=True).start()

    while True:
        peer_ip = input("\nEnter peer IP to connect (or 'exit' to quit): ").strip()
        if peer_ip.lower() == "exit":
            break
        peer_client(peer_ip)

if __name__ == "__main__":
    main()
