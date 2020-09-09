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
final_frame = b''

def create_listener():
    global conn
    global final_frame
    
    HOST='localhost'
    PORT=8096

    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    print('Socket created')

    s.bind((HOST,PORT))
    print('Socket bind complete')
    s.listen(10)
    print('Socket now listening')

    while True:        
        conn,addr=s.accept()

        data = b""
        payload_size = struct.calcsize(">L")
        print("payload_size: {}".format(payload_size))
        # return conn, data, payload_size

        try:
            while True:
                while len(data) < payload_size:
                    print("Recv: {}".format(len(data)))
                    data += conn.recv(4096)

                print("Done Recv: {}".format(len(data)))
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]
                print("msg_size: {}".format(msg_size))
                while len(data) < msg_size:
                    data += conn.recv(4096)
                frame_data = data[:msg_size]
                data = data[msg_size:]

                frame=pickle.loads(frame_data, fix_imports=True, encoding="bytes")
                print(type(frame))
                im = Image.fromarray(frame)
                # frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                
                # ret, jpeg = cv2.imencode('.jpg', frame)
                final_frame = im.tobytes()  # jpeg.tobytes()
                # cv2.imshow('ImageWindow',frame)
                # cv2.waitKey(1)
        finally:
            conn.close()

def get_frame():
    global final_frame
    while True:
        print(final_frame)    
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + final_frame + b'\r\n\r\n')


@app.route('/')
def index():
    template = """
    <html>
        <head>
            <title>Video Streaming Demonstration</title>
        </head>
        <body>
            <h1>Video Streaming Demonstration</h1>
            <img id="bg" src="{{ url_for('video_feed') }}">
        </body>
    </html>
    """
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    try:
        t = threading.Thread(target=create_listener)
        t.daemon = True
        t.start()
        app.run(debug=True, port=3000)
    except Exception:
        conn.close()
    
    