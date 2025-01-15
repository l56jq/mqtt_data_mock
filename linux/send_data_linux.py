import paho.mqtt.client as mqtt
import random
import time
import json
from datetime import datetime, timedelta
import threading


# 加载配置文件
def load_config(file_path):
    config = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                key, value = line.strip().split('=')
                config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Configuration file {file_path} not found.")
    except Exception as e:
        print(f"Error reading configuration file: {e}")
    return config


# MQTT 连接回调
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
    else:
        print(f"Failed to connect, return code {rc}")


# 发送数据的函数，每个点位单独一个线程
def send_data(client, point, topic):
    global running
    while running:
        data = {
            point: [{
                f"test{i}": round(random.uniform(-100, 100), 2) for i in range(1, 201)
            }]
        }
        payload = json.dumps(data)
        client.publish(topic, payload)
        data_sent_count[point] += 1
        time.sleep(1)  # 每秒发送一次


# 主程序
if __name__ == "__main__":
    config_path = 'mqtt_config.txt'  # 配置文件路径
    config = load_config(config_path)

    if not config:
        print("Configuration loading failed, exiting.")
        exit(1)

    client_id = f'client_{random.randint(1000, 9999)}'

    mqtt_ip = config.get("mqtt_ip", "")
    mqtt_port = int(config.get("mqtt_port", 1883))
    mqtt_username = config.get("mqtt_username", "")
    topic = config.get("topic", "")
    hours = int(config.get("hours", 1))

    points_path = 'points.txt'
    try:
        with open(points_path, 'r') as file:
            points = file.read().strip().split(',')
    except FileNotFoundError:
        print(f"Points file {points_path} not found.")
        exit(1)

    data_sent_count = {point: 0 for point in points}
    running = True

    mqtt_client = mqtt.Client(client_id=client_id)
    mqtt_client.username_pw_set(mqtt_username)
    mqtt_client.on_connect = on_connect

    try:
        mqtt_client.connect(mqtt_ip, mqtt_port, keepalive=120)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        running = False

    start_time = datetime.now()
    print(f"Start time: {start_time}")

    # 计算最大运行时间
    max_duration = timedelta(hours=hours)
    end_time_limit = start_time + max_duration

    try:
        # 为每个点位启动一个线程
        threads = []
        for point in points:
            thread = threading.Thread(target=send_data, args=(mqtt_client, point, topic))
            thread.start()
            threads.append(thread)

        while running and datetime.now() < end_time_limit:
            time.sleep(1)

        running = False  # 停止所有线程
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        running = False
        for thread in threads:
            thread.join()  # 等待所有数据发送线程结束
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

        end_time = datetime.now()
        print(f"End time: {end_time}")

        duration = end_time - start_time
        print(f"Total running time: {duration}")
        print("Data sent count:", data_sent_count)
