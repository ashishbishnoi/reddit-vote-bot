from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog
from PyQt5.QtCore import QTimer, QTime
import sys
import requests, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys
import csv
from itertools import cycle
import threading
from datetime import datetime
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QListWidget, QFormLayout

class Worker(QObject):
    updated = pyqtSignal(int)

    def __init__(self, ads_id_gen, subreddit, text, total_upvotes, no_of_threads, delay, action):
        super().__init__()
        self.ads_id_gen = ads_id_gen
        self.subreddit = subreddit
        self.text = text
        self.total_upvotes = total_upvotes
        self.no_of_threads = no_of_threads
        self.delay = delay
        self.action = action

    def process(self):
        upvotes_count = 0

        while upvotes_count < self.total_upvotes:
            active_threads = []

            for _ in range(self.no_of_threads):
                if upvotes_count >= self.total_upvotes:
                    break

                try:
                    ads_id = next(self.ads_id_gen, None)
                    if not ads_id:
                        break

                    t = threading.Thread(target=self.reddit_login_thread, args=(ads_id, self.subreddit, self.text))
                    t.daemon = True
                    t.start()
                    active_threads.append(t)
                    time.sleep(15)
                    upvotes_count += 1
                    self.updated.emit(upvotes_count)
                except Exception as e:
                    print(f"An error occurred: {e}")

            for t in active_threads:
                t.join()

            if upvotes_count < self.total_upvotes:
                time.sleep(self.delay * 60)


    def reddit_login_thread(self,ads_id,subreddit,text):
        open_url = "http://local.adspower.net:50325/api/v1/browser/start?user_id=" + ads_id
        close_url = "http://local.adspower.net:50325/api/v1/browser/stop?user_id=" + ads_id
        resp = requests.get(open_url).json()
        if resp["code"] != 0:
            print(resp["msg"])
            print("please check ads_id")
            sys.exit()

        self.reddit_login(ads_id, subreddit, text,resp)
        #requests.get(close_url)

    

    def reddit_login(self,ads_id,subreddit, text,resp):
        chrome_driver = resp["data"]["webdriver"]
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", resp["data"]["ws"]["selenium"])
        driver = webdriver.Chrome(chrome_driver, options=chrome_options)
        close_url = "http://local.adspower.net:50325/api/v1/browser/stop?user_id=" + ads_id
        print(driver.title)
        driver.get('https://reddit.com')
        time.sleep(10)
        driver.get(subreddit)
        time.sleep(7)
        buttonClick = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(((By.CSS_SELECTOR, f"[href='{text}']"))))
        ActionChains(driver).move_to_element(buttonClick).click().perform()
        #WebDriverWait(driver, timeout=5).until(lambda d: d.find_element(By.LINK_TEXT, text)).click()
        driver.execute_script("window.scrollTo(0,300)")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0,100)")
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, 220)")
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, 0)")
        #buttonClick = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="upvote-button-t3_12susv1]')))
        #ActionChains(driver).move_to_element(buttonClick).click().perform()
        time.sleep(5)
        if self.action == "upvote":
            WebDriverWait(driver, timeout=5).until(lambda d: d.find_element(By.CSS_SELECTOR,"div.arrow.up")).click()
        elif self.action == "downvote":
            WebDriverWait(driver, timeout=5).until(lambda d: d.find_element(By.CSS_SELECTOR,"div.arrow.down")).click()
        driver.refresh()
        time.sleep(5)
        for i in driver.window_handles:
            driver.switch_to.window(i)
            driver.close()
        driver.quit()
        requests.get(close_url)


class RedditAutomation(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Reddit Automation")
        
        # Create input fields and labels
        self.subreddit_label = QLabel("Subreddit URL:", self)
        self.subreddit_entry = QLineEdit(self)
        self.text_label = QLabel("Text:", self)
        self.text_entry = QLineEdit(self)
        self.csv_file_label = QLabel("CSV File:", self)
        self.csv_file_path = QLineEdit(self)
        self.time_picker_label = QLabel("Schedule time:", self)
        self.time_picker = QLineEdit("00:00", self)
        self.total_upvotes_label = QLabel("Total Votes:", self)
        self.total_upvotes_entry = QLineEdit(self)
        self.no_of_threads_label = QLabel("No of threads:", self)
        self.no_of_threads_entry = QLineEdit(self)
        self.delay_label = QLabel("Delay:", self)
        self.delay_entry = QLineEdit(self)

        # Create labels for current upvotes and remaining upvotes
        self.current_upvotes_label = QLabel("Upvotes Done: 0", self)
        self.remaining_upvotes_label = QLabel("Upvotes in Queue: 0", self)

        # Create buttons
        self.browse_button = QPushButton("Browse", self)
        self.upvote_button = QPushButton("Upvote Now", self)
        self.downvote_button = QPushButton("Downvote Now", self)
        self.schedule_upvotes_button = QPushButton("Schedule Upvotes", self)
        self.schedule_downvotes_button = QPushButton("Schedule Downvotes", self)


        # Connect button actions
        self.browse_button.clicked.connect(self.browse_csv_file)
        self.upvote_button.clicked.connect(self.start_upvote_process)
        self.downvote_button.clicked.connect(self.start_downvote_process)
        self.schedule_upvotes_button.clicked.connect(self.schedule_upvote_process)
        self.schedule_downvotes_button.clicked.connect(self.schedule_downvote_process)

        # Create a horizontal layout for the  buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.upvote_button)
        button_layout.addWidget(self.downvote_button)
        schedule_button_layout = QHBoxLayout()
        schedule_button_layout.addWidget(self.schedule_upvotes_button)
        schedule_button_layout.addWidget(self.schedule_downvotes_button)
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.current_upvotes_label)
        status_layout.addWidget(self.remaining_upvotes_label)

        # Create a list to store the timers and a QListWidget to display them
        self.timers = []
        self.scheduled_tasks_list = QListWidget(self)

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.scheduled_tasks_list)
        layout.addWidget(self.subreddit_label)
        layout.addWidget(self.subreddit_entry)
        layout.addWidget(self.text_label)
        layout.addWidget(self.text_entry)
        layout.addWidget(self.csv_file_label)
        layout.addWidget(self.csv_file_path)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.time_picker_label)
        layout.addWidget(self.time_picker)
        layout.addLayout(button_layout)
        layout.addLayout(schedule_button_layout)
        layout.addWidget(self.total_upvotes_label)
        layout.addWidget(self.total_upvotes_entry)
        layout.addWidget(self.no_of_threads_label)
        layout.addWidget(self.no_of_threads_entry)
        layout.addWidget(self.delay_label)
        layout.addWidget(self.delay_entry)
        layout.addLayout(status_layout)
        # Set window layout
        self.setLayout(layout)

    def start_upvote_process(self):
        self.start_process("upvote")

    def start_downvote_process(self):
        self.start_process("downvote")

    def schedule_upvote_process(self):
        self.schedule_process("upvote")

    def schedule_downvote_process(self):
        self.schedule_process("downvote")

    def schedule_process(self, action):
        selected_time = self.time_picker.text()
        text = self.text_entry.text()
        now = datetime.now()
        target_time = datetime.strptime(selected_time, "%H:%M").time()

        if target_time < now.time():
            tomorrow = now.date() + timedelta(days=1)
            target_datetime = datetime.combine(tomorrow, target_time)
        else:
            target_datetime = datetime.combine(now.date(), target_time)

        delay = (target_datetime - now).total_seconds()
        timer = threading.Timer(delay, self.start_process, [action])
        timer.start()
        self.timers.append(timer)
        self.scheduled_tasks_list.addItem(f"Scheduled {action} for '{text}' at {selected_time}")

    def browse_csv_file(self):
        file_dialog = QFileDialog()
        file_path = file_dialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        self.csv_file_path.setText(file_path[0])

    def start_process(self, action):
        subreddit = self.subreddit_entry.text()
        text = self.text_entry.text()
        csv_path = self.csv_file_path.text()
        total_upvotes = int(self.total_upvotes_entry.text())
        no_of_threads = int(self.no_of_threads_entry.text())
        delay = float(self.delay_entry.text())

        ads_id_gen = self.csv_rows_generator(csv_path)

        if action == "upvote":
            self.worker = Worker(ads_id_gen, subreddit, text, total_upvotes, no_of_threads, delay, action="upvote")
        elif action == "downvote":
            self.worker = Worker(ads_id_gen, subreddit, text, total_upvotes, no_of_threads, delay, action="downvote")

        self.worker.updated.connect(self.update_upvotes)

        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.process)
        self.thread.start()

    @pyqtSlot(int)
    def update_upvotes(self, count):
        total_upvotes = int(self.total_upvotes_entry.text())
        remaining_upvotes = total_upvotes - count

        self.current_upvotes_label.setText(f"Current Upvotes: {count}")
        self.remaining_upvotes_label.setText(f"Upvotes in Queue: {remaining_upvotes}")


    def csv_rows_generator(self,csv_path):
        with open(csv_path, newline='') as csvfile:
            csvreader = csv.reader(csvfile)
            for row in csvreader:
                yield row[0]

    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    reddit_automation = RedditAutomation()
    reddit_automation.show()
    sys.exit(app.exec_())

