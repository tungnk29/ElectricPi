from module.IoTClient import PiMethods
import json, time, os, logging, requests
import asyncio
import signal
import uvloop
from gmqtt import Subscription, Message, Client as MQTTClient
# from gmqtt.mqtt.constants import MQTTv311

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
STOP = asyncio.Event()

PI = PiMethods()
TOKEN = PI.TOKEN
HOST = PI.HOST
PORT = PI.PORT

URL = f'http://{HOST}:{PORT}'


topic_status = f'pop/{TOKEN}/status'
topic_execute = f'pop/{TOKEN}/execute'
topic_data = 'pop/push/data'


def ask_exit(*args):
    STOP.set()


def on_connect(client, flags, rc, properties):
    print(f"connected OK Returned code={rc}")
    print(f'subscribing topic {topic_execute} ...')
    status = json.dumps({'connected': True, 'token': TOKEN})
    client.publish(topic_status, payload=status, qos=1, retain=1, message_expiry_interval=20)
    # client.subscribe(topic_execute, qos=1, retain=1)
    client.subscribe([Subscription(topic_execute, qos=2), Subscription(topic_data, qos=0)], subscription_identifier=2)

def on_disconnect(client, packet, exc=None):
    print('Disconnected')

def on_subscribe(client, mid, qos, properties):
    print('SUBSCRIBED')

async def on_message(client, topic, payload, qos, properties):
    print(f"Message arrive from {topic} ")
    data = json.loads(PI.CIPHER.decrypt(payload))
    PI.recv_package(data)

        
        
async def main():
    # LWT
    status_lwt = json.dumps({'connected': False, 'token': TOKEN})

    will_message = Message(topic_status, status_lwt, qos=1, retain=1, will_delay_interval=10)

    # Main client
    client = MQTTClient(client_id=TOKEN, will_message=will_message)
    client.set_config({'reconnect_retries': 10, 'reconnect_delay': 60})

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    client.set_auth_credentials(TOKEN, TOKEN)
    await client.connect(HOST, 1883,)

    # loop.create_task(push_data(client))

    await STOP.wait()
    await client.disconnect(reason_code=4, reason_string="Something went wrong!")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    logging.basicConfig(level=logging.INFO)

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    loop.run_until_complete(main())

