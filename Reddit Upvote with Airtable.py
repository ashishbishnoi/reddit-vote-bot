from flask import Flask, request
import threading
import time
import csv
import sys
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

app = Flask(__name__)

class Worker():
    def __init__(self, ads_id_gen, subreddit, text, total_upvotes, no_of_threads, delay, action):
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
                    app.logger.info(f'Upvotes Done: {upvotes_count}')
                except Exception as e:
                    app.logger.error(f"An error occurred: {e}")

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

def csv_rows_generator(csv_path):
    with open(csv_path, newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            print(row[0])
            yield row[0]

@app.route('/start_process', methods=['POST'])
def start_process():
    data = request.json
    subreddit = data['subreddit']
    text = data['text']
    csv_path = data['csv_path']
    total_upvotes = int(data['total_upvotes'])
    no_of_threads = int(data['no_of_threads'])
    delay = float(data['delay'])
    action = data['action']
    print(csv_path)
    ads_id_gen = csv_rows_generator(csv_path)

    worker = Worker(ads_id_gen, subreddit, text, total_upvotes, no_of_threads, delay, action)
    worker.process()

    return {'message': 'Process started'}

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)







