import socket
from time import sleep

SERVER_CONFIG = ("localhost", 50000)  # Server address and port
MESSAGE = "95041 181111E40101002"  # Example message to send

# Create a TCP/IP socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

    # Connect the socket to the port where the server is listening
    print("connecting to %s port %s" % SERVER_CONFIG)
    sock.connect(SERVER_CONFIG)

    try:
        enc_mes = bytes(MESSAGE.encode("utf-8"))
        print('sending "%s"' % MESSAGE)
        sock.sendall(enc_mes)

        chunk = 1024
        data = sock.recv(chunk)

        # dec_data = data.decode('utf-8')
        print('Received acknowledgement succesfully "%s"' % data)
    except Exception as e:
        print(f"failed to send data : {e}")
    finally:
        sleep(1)
        print("closing socket")
        sock.close()