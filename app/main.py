#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
import matplotlib.pyplot as plt
import rosbag
import roslib.message
import os

BLACK = "#000000"
GRAY1 = "#303030"
GRAY2 = "#909090"
WHITE = "#FFFFFF"

class MainWindow():
    def __init__(self, w=600, h=600, wx=100, wy=100):
        self.width = w
        self.height = h
        self.window_x = wx
        self.window_y = wy
        self.button1_x = 300
        self.button1_y = 100
        self.button2_x = 500
        self.button2_y = 500
        self.setup_window()
        self.setup_canvas()
        self.setup_button_open_file()
        self.setup_button_reset()
        self.file_name = None
        self.topics = []
        self.topic_types = {}

    def close(self, event):
        self.window.destroy()

    def open_file(self, event):
        file_name = filedialog.askopenfilename()
        # canceled
        if not file_name:
            return
        self.file_name = os.path.normpath(os.path.join(os.getcwd(), file_name))
        print(self.file_name)
        with rosbag.Bag(self.file_name) as bag:
            info = bag.get_type_and_topic_info()
        self.topic_types = {topic: val.msg_type for topic, val in info.topics.items()}
        self.topics = list(self.topic_types.keys())
        for topic in self.topics:
            print(topic)
        self.open_selection_dialog()

    def open_selection_dialog(self):
        topic_dialog = SelectionDialog(self.window, "Select topic", self.topics)
        selected_topic = topic_dialog.selected
        print(selected_topic)
        if selected_topic is None:
            print("Cannot get topic.")
            return
        msg_class = roslib.message.get_message_class(self.topic_types[selected_topic])
        if msg_class is None:
            print("Cannot get message class:", self.topic_types[selected_topic])
            return
        fields = self.build_msg_tree(msg_class)
        field_dialog = SelectionDialog(self.window, "Select field", fields)
        selected_field = field_dialog.selected
        if selected_field is None:
            print("Cannot get field.")
            return

        print("result:", selected_topic, selected_field)

    def reset(self, event):
        self.file_name = None
        self.topics = []
        self.topic_types = {}

    def setup_window(self):
        self.window = tk.Tk()
        self.window.title("TEST")
        self.window.geometry(f"{self.width}x{self.height}+{self.window_x}+{self.window_y}")

    def setup_canvas(self):
        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height, background=GRAY1)
        self.canvas.place(x=0, y=0)

    def setup_button_open_file(self):
        self.button_open_file = tk.Button(self.window, text="OPEN FILE", background=WHITE, activebackground=GRAY2)
        self.button_open_file.bind("<Button-1>", self.open_file)
        self.button_open_file.place(x=self.button1_x, y=self.button1_y)

    def setup_button_reset(self):
        self.button_reset = tk.Button(self.window, text="RESET", background=WHITE, activebackground=GRAY2)
        self.button_reset.bind("<Button-1>", self.reset)
        self.button_reset.place(x=self.button1_x, y=self.button1_y+100)


    @staticmethod
    def build_msg_tree(msg, prefix=""):
        fields = []

        for slot, slot_type in zip(msg.__slots__, msg._slot_types):
            name = f"{prefix}.{slot}" if prefix else slot

            # nest
            if "/" in slot_type:
                sub_msg_class = roslib.message.get_message_class(slot_type)
                if sub_msg_class is None:
                    continue
                fields.extend(MainWindow.build_msg_tree(sub_msg_class, name))
            else:
                fields.append(name)

        return fields

    def main(self):
        self.window.bind("<q>", self.close)

# selection of topic
class SelectionDialog(simpledialog.Dialog):
    def __init__(self, parent, title, items):
        self.items = list(items)
        self.selected = None
        super().__init__(parent, title)

    def body(self, master):
        self.listbox = tk.Listbox(master, width=50, height=30)
        for item in self.items:
            self.listbox.insert(tk.END, item)
        self.listbox.pack()
        return self.listbox

    def apply(self):
        selection = self.listbox.curselection()
        if selection:
            self.selected = self.items[selection[0]]

if __name__ == "__main__":
    App = MainWindow()
    App.main()
    App.window.mainloop()
    
