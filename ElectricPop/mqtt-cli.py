from cryptography.fernet import Fernet
from datetime import datetime
from threading import Thread
from module.IoTClient import PiMethods
import json, time, requests
import paho.mqtt.client as mqtt


PI = PiMethods()
TOKEN = PI.TOKEN
HOST = PI.HOST

broker_port = 1883

rc_message = [
        'Connection successful',
        'Connection refused – incorrect protocol version',
        'Connection refused – invalid client identifier',
        'Connection refused – server unavailable',
        'Connection refused – bad username or password',
        'Connection refused – not authorised'
    ]


topic_status = f'pop/{TOKEN}/status'
topic_execute = f'pop/{TOKEN}/execute'
topic_data = 'pop/push/data'

def on_publish(client, obj, mid):
    print("mid: " + str(mid))

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True #set flag
        print("connected OK Returned code=",rc)

        status = json.dumps({'connected': True, 'token': TOKEN})
        client.publish(topic_status, payload=status, qos=1, retain=1)
        client.subscribe([(topic_execute, 2), (topic_data, 0)])

        return
        
    print("Bad connection Returned code= ",rc)
    client.bad_connection_flag = True

def on_disconnect(client, userdata, rc):
    print("Client got disconnected!")
    print(rc, ': ', rc_message[rc])

    client.connected_flag = False
    client.disconnect_flag = True

def on_message(mosq, obj, msg):    
    if (msg.topic == topic_execute or msg.topic == topic_data):
        print("Message arrive  from %s " % msg.topic)
        data = json.loads(PI.CIPHER.decrypt(msg.payload))
        PI.recv_package(data)

def on_subscribe(client, userdata, mid, granted_qos):
    print(f'subscribed topic with data: {userdata} ')

# Init client mqtt
client = mqtt.Client(client_id=f'{TOKEN}{datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}', clean_session=True)
client.username_pw_set(TOKEN, TOKEN)

# LWT
status_lwt = json.dumps({'connected': False, 'token': TOKEN})
client.will_set(topic_status, payload=status_lwt, qos=1, retain=True)

# Callback
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_publish = on_publish
client.on_subscribe = on_subscribe

# Connect & Subscribe
client.connect(HOST, broker_port, keepalive=60)
# client.subscribe([(topic_execute, 1), (topic_data, 0)])

client.loop_forever()




