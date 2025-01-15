import tkinter as tk
from tkinter import filedialog, messagebox
import json
import random
import time
import os
import threading
import paho.mqtt.client as mqtt


class MQTTClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MQTT Client")
        self.root.geometry("800x600")
        self.root.resizable(False, False)  # Disable window resizing

        # MQTT Configuration
        self.config_file = "mqtt_config.json"
        self.mqtt_ip = tk.StringVar()
        self.mqtt_port = tk.IntVar()
        self.mqtt_username = tk.StringVar()
        self.client_id = tk.StringVar()
        self.topic = tk.StringVar()

        self.load_config()

        if not self.client_id.get():
            self.client_id.set(f'client_{random.randint(1000, 9999)}')

        self.mqtt_client = None
        self.running = False
        self.points = []
        self.threads = []
        self.data_sent_count = {point: 0 for point in self.points}

        # UI Elements
        self.create_widgets()

    def create_widgets(self):
        # 居中框架
        self.center_frame = tk.Frame(self.root)
        self.center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 输入框和标签
        self.add_label_entry("MQTT IP:", self.mqtt_ip, 0)
        self.add_label_entry("MQTT Port:", self.mqtt_port, 1)
        self.add_label_entry("MQTT Username:", self.mqtt_username, 2)
        self.add_label_entry("Client ID:", self.client_id, 3)
        self.add_label_entry("MQTT Topic:", self.topic, 4)

        # 按钮
        self.connect_button = tk.Button(self.center_frame, text="Connect", command=self.connect_to_mqtt)
        self.connect_button.grid(row=5, column=0, padx=5, pady=5, sticky='e')

        self.disconnect_button = tk.Button(self.center_frame, text="Disconnect", command=self.disconnect_from_mqtt,
                                           state=tk.DISABLED)
        self.disconnect_button.grid(row=5, column=1, padx=5, pady=5, sticky='w')

        self.import_button = tk.Button(self.center_frame, text="Import Points", command=self.import_points,
                                       state=tk.DISABLED)
        self.import_button.grid(row=6, column=0, columnspan=2, pady=10)

        self.start_button = tk.Button(self.center_frame, text="Start Test", command=self.start_test, state=tk.DISABLED)
        self.start_button.grid(row=7, column=0, padx=5, pady=5, sticky='e')

        self.stop_button = tk.Button(self.center_frame, text="Stop Test", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.grid(row=7, column=1, padx=5, pady=5, sticky='w')

        # Status Labels
        self.status_label = tk.Label(self.center_frame, text="Status: Disconnected", bg="lightblue", font=('Arial', 10))
        self.status_label.grid(row=8, column=0, columnspan=2, pady=10)

        self.time_label = tk.Label(self.center_frame, text="Time Elapsed: 00:00:00", bg="lightblue", font=('Arial', 10))
        self.time_label.grid(row=9, column=0, columnspan=2, pady=10)

        self.points_label = tk.Label(self.center_frame, text="Imported Points: None", bg="lightblue",
                                     font=('Arial', 10))

        # 停止时间标签
        self.stop_time_label = tk.Label(self.center_frame, text="Stop Time: Not stopped yet", bg="lightblue", font=('Arial', 10))
        self.stop_time_label.grid(row=11, column=0, columnspan=2, pady=10)

        self.points_label.grid(row=10, column=0, columnspan=2, pady=10)

    def add_label_entry(self, text, var, row):
        label = tk.Label(self.center_frame, text=text, bg="lightblue", font=('Arial', 10))
        label.grid(row=row, column=0, padx=5, pady=5, sticky='e')
        entry = tk.Entry(self.center_frame, textvariable=var, width=30, font=('Arial', 10))
        entry.grid(row=row, column=1, padx=5, pady=5, sticky='w')

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                config = json.load(file)
                self.mqtt_ip.set(config.get("mqtt_ip", ""))
                self.mqtt_port.set(config.get("mqtt_port", 1883))
                self.mqtt_username.set(config.get("mqtt_username", ""))
                self.client_id.set(config.get("client_id", ""))
                self.topic.set(config.get("topic", ""))

    def save_config(self):
        config = {
            "mqtt_ip": self.mqtt_ip.get(),
            "mqtt_port": self.mqtt_port.get(),
            "mqtt_username": self.mqtt_username.get(),
            "client_id": self.client_id.get(),
            "topic": self.topic.get()
        }
        with open(self.config_file, 'w') as file:
            json.dump(config, file)

    def connect_to_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(client_id=self.client_id.get())
            self.mqtt_client.username_pw_set(self.mqtt_username.get())
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_disconnect = self.on_disconnect
            # self.mqtt_client.on_log = self.on_log  # Optional: log MQTT events for debugging
            self.mqtt_client.connect(self.mqtt_ip.get(), self.mqtt_port.get(), keepalive=120)
            self.mqtt_client.loop_start()
            self.status_label.config(text="Status: Connecting...")
            self.save_config()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to MQTT: {str(e)}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.status_label.config(text="Status: Connected")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.import_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text=f"Status: Connection failed (rc={rc})")

    def on_disconnect(self, client, userdata, rc):
        self.status_label.config(text="Status: Disconnected")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.import_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        if self.running:
            self.connect_to_mqtt()  # Attempt to reconnect if running

    def on_log(self, client, userdata, level, buf):
        print(f"Log: {buf}")

    def disconnect_from_mqtt(self):
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None
        self.status_label.config(text="Status: Disconnected")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.import_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

    def import_points(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, 'r') as file:
                self.points = file.read().strip().split(',')
            # self.points_label.config(text=f"Imported Points: {', '.join(self.points)}")
            self.data_sent_count = {point: 0 for point in self.points}
            self.show_points_and_stats()

    def show_points_and_stats(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Point Information")
        stats_window.geometry("300x400")

        tk.Label(stats_window, text="Points Information:", bg="lightblue").pack(pady=10)

        self.points_listbox = tk.Listbox(stats_window)
        self.points_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.update_points_listbox()

        stats_label = tk.Label(stats_window, text="Data Sent Count:", bg="lightblue")
        stats_label.pack(pady=10)

        self.stats_count_label = tk.Label(stats_window, text="", bg="lightblue")
        self.stats_count_label.pack(pady=10)

        # self.update_stats_window()

    def update_points_listbox(self):
        self.points_listbox.delete(0, tk.END)
        for point in self.points:
            self.points_listbox.insert(tk.END, point)

    def start_test(self):
        if not self.mqtt_client:
            messagebox.showwarning("Warning", "Please connect to MQTT first.")
            return
        if not self.points:
            messagebox.showwarning("Warning", "Please import points first.")
            return

        self.running = True
        self.data_sent_count = {point: 0 for point in self.points}
        self.start_time = time.time()
        self.update_timer()

        # Start a thread for each point to send data
        self.threads = []
        for point in self.points:
            t = threading.Thread(target=self.send_data_for_point, args=(point,))
            t.start()
            self.threads.append(t)

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_test(self):
        self.running = False
        for t in self.threads:
            t.join()  # Wait for all threads to finish

        # 更新停止时间
        stop_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.stop_time_label.config(text=f"Stop Time: {stop_time}")

        self.stop_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)

    def update_timer(self):
        if self.running:
            elapsed_time = int(time.time() - self.start_time)
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.config(text=f"Time Elapsed: {hours:02}:{minutes:02}:{seconds:02}")
            self.root.after(1000, self.update_timer)

    def send_data_for_point(self, point):
        while self.running:
            data = {
                point: [{
                    f"test{i}": round(random.uniform(-100, 100), 2) for i in range(1, 201)
                }]
            }
            payload = json.dumps(data)
            self.mqtt_client.publish(self.topic.get(), payload)
            self.data_sent_count[point] += 1
            time.sleep(1)  # Send data every second

    def on_closing(self):
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MQTTClientApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
