import signal
import atexit
import socket
import sys
import cv2
import pickle
import numpy as np
import struct ## new
import threading
from PIL import Image
from flask import Flask, Response, render_template, g

app = Flask(__name__)

conn = None
cam_frame = b''
stop_threads = False

VIDEO_STREAM_HOST = '0.0.0.0'
VIDEO_STREAM_SOCKET_PORT = '8096'

def create_listener():
    global conn, cam_frame, stop_threads
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((VIDEO_STREAM_HOST, VIDEO_STREAM_SOCKET_PORT))
        print('Socket bind complete')
        s.listen(10)
        print('Socket now listening')

        while True:
            conn, addr = s.accept()
            data = b""
            payload_size = struct.calcsize(">L")

            if stop_threads:
                conn.close()
                break

            while True:
                counter = 0
                while len(data) < payload_size:
                    counter += 1
                    data += conn.recv(4096)
                    if counter == 10:
                        break
                if counter == 10:
                    break

                print("Done Recv: {}".format(len(data)))
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]
                # print("msg_size: {}".format(msg_size))
                while len(data) < msg_size:
                    data += conn.recv(4096)
                frame_data = data[:msg_size]
                data = data[msg_size:]
                frame = pickle.loads(frame_data, fix_imports=True, encoding="bytes")
                im = Image.fromarray(frame)
                cam_frame = im.tobytes()  # jpeg.tobytes()
                print('Cam1 Feed RECEIVED')

                if stop_threads:
                    conn.close()
                    break

def get_frame():
    global cam_frame
    while True:
        # print(cam_frame)    
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + cam_frame + b'\r\n\r\n')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

t1 = Thread(target=create_listener).start()

def sig_handler(signum=None, frame=None):
    global stop_threads, conn
    if conn:
        conn.close()
    stop_threads = True
    sys.exit(0)


atexit.register(sig_handler)
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)


if __name__ == '__main__':
    try:
        app.run(debug=True, port=3000, use_reloader=False)
    except Exception:
        sys.exit(0)
    
    
