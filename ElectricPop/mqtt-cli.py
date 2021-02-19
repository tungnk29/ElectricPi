from paho.mqtt import client as mqtt_client
from module.IoTClient import PiMethods
import json, time, requests

PI = PiMethods()
TOKEN = PI.TOKEN
HOST = PI.HOST
PORT = PI.PORT

URL = f'http://{HOST}:{PORT}'

broker_port = 1883

topic_status = f'pop/{TOKEN}/status'
topic_execute = f'pop/{TOKEN}/execute'
topic_data = f'pop/{TOKEN}/data'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            print(f'subscribing topic {topic_execute} ...')
            status = json.dumps({'connected': True, 'token': TOKEN})
            client.publish(topic_status, payload=status, qos=1, retain=1)
            # client.subscribe(topic_execute, qos=1, retain=1)
        else:
            print("Failed to connect, return code %d\n", rc)

    status_lwt = json.dumps({'connected': False, 'token': TOKEN})

    client = mqtt_client.Client(TOKEN)
    client.username_pw_set(TOKEN, TOKEN)
    client.on_connect = on_connect
    client.will_set(topic, payload=status_lwt, qos=1, retain=True)
    client.connect(HOST, broker_port)
    return client

def subscribe(client):
    def on_message(client, userdata, msg):
        print(f"Message arrive from {topic} ")
        data = json.loads(PI.CIPHER.decrypt(msg.payload))
        PI.recv_package(data)

    client.subscribe(topic_execute)
    client.on_message = on_message

def publish():
    while True:
        time.sleep(5)
        data_powermeter = PI.process_data(PI.data_powermeter())
        pop_status = PI.process_data(PI.pop_status())
        try:
            post_data = requests.post(f'{URL}/data/push', data={ 'message': data_powermeter })
            post_status = requests.post(f'{URL}/pops/status', data={ 'message': pop_status })
        except Exception as err:
            print(err)

def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()

if __name__ == '__main__':
    run()

