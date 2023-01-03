import json
import os.path
import time
from threading import Thread, Semaphore, Lock

# import requests
from bs4 import BeautifulSoup
import traceback
from datetime import datetime

from random_user_agent.user_agent import UserAgent
from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

t = 1
timeout = 10

debug = False

headless = False
images = False
maximize = False

incognito = False
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
headers = {
    'user-agent': ua
}

size = 100
at = "https://www.autotrader.ca"
semaphore = Semaphore(1)
lock = Lock()


def get(url):
    # return requests.get(url, headers=headers)
    # with lock:
    driver.get(url)
    time.sleep(1)
    return driver.page_source


def getData(url):
    with semaphore:
        r = get(url)
        id_ = url.split('/')[-2]
        html = f'./html/{id_}.html'
        if os.path.isfile(f'./data/{id_}.json'):
            print(f"[+] {url} already scraped")
            return
        print(f"[+] Scraping {url}")
        if os.path.isfile(html):
            with open(html, 'r') as f:
                r = f.read()
        else:
            with open(html, 'w') as f:
                f.write(r)
        soup = BeautifulSoup(r, 'html.parser')
        data = {'URL': url}
        # print(r.text)
        js = None
        for script in soup.find_all('script', {"type": "text/javascript"}):
            if "window['ngVdpModel'] =" in script.text:
                for line in script.text.splitlines():
                    if "window['ngVdpModel'] =" in line:
                        js = json.loads(line.replace("window['ngVdpModel'] =", '').strip()[:-1])
                        # script = line.strip()[:-1]
                        break
            if js:
                break
        # print(json.dumps(js, indent=4))
        with open('data.json', 'w') as f:
            json.dump(js, f, indent=4)
        data['Title'] = soup.find('title').text
        data['Image'] = soup.find("meta", {"property": "og:image"})['content']
        data['Province'] = js['deepLinkSavedSearch']['savedSearchCriteria']['provinceAbbreviation']
        for key, val in js['hero'].items():
            if key in ['year', 'price', 'mileage']:
                data[key.title()] = int(val.replace(',', '').replace('$', '').replace('km', '').strip())
            elif key in ['make', 'model', 'trim', 'vin']:
                data[key.title()] = val
        if 'featureHighlights' in js and 'options' in js['featureHighlights']:
            data['Features'] = js['featureHighlights']['options']
        data['Specs'] = js['specifications']['specs']
        data['Hero'] = js['hero']
        # print(json.dumps(data, indent=4))
        with open(f'./data/{id_}.json', 'w') as f:
            json.dump(data, f, indent=4)
        return data


def main():
    if not os.path.isdir('html'):
        os.mkdir('html')
    if not os.path.isdir('data'):
        os.mkdir('data')
    # url = 'https://www.autotrader.ca/a/bmw/7%20series/boucherville/quebec/5_54555424_20090324114217770/'
    # getData(url)
    threads = []
    for i in range(1000):
        url = f"{at}/cars/?rcp={size}&rcs={i * size}"
        print(f"[+] Page URL {url}")
        r = get(url)
        soup = BeautifulSoup(r, 'html.parser')
        urls = soup.find_all('a', {"class": "result-title click"})
        if len(urls) == 0:
            print("[+] No more pages")
            with open('error.html', 'w') as efile:
                efile.write(r)
            break
        for a in urls:
            t = Thread(target=getData, args=(f"{at}{a['href']}",))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()


def logo():
    print(r"""
       _____          __           ___________                  .___            
      /  _  \  __ ___/  |_  ____   \__    ___/___________     __| _/___________ 
     /  /_\  \|  |  \   __\/  _ \    |    |  \_  __ \__  \   / __ |/ __ \_  __ \
    /    |    \  |  /|  | (  <_> )   |    |   |  | \// __ \_/ /_/ \  ___/|  | \/
    \____|__  /____/ |__|  \____/    |____|   |__|  (____  /\____ |\___  >__|   
            \/                                           \/      \/    \/       
====================================================================================
             AutoTrader.CA scraper by github.com/evilgenius786
====================================================================================
[+] Automated
[+] Without browser
[+] CSV/JSON Output
[+] Resumable
____________________________________________________________________________________
""")


def pprint(msg):
    try:
        print(f"{datetime.now()}".split(".")[0], msg)
    except:
        traceback.print_exc()



def click(driver, xpath, js=False):
    if js:
        driver.execute_script("arguments[0].click();", getElement(driver, xpath))
    else:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()


def getElement(driver, xpath):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))


def getElements(driver, xpath):
    return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((By.XPATH, xpath)))


def sendkeys(driver, xpath, keys, js=False):
    if js:
        driver.execute_script(f"arguments[0].value='{keys}';", getElement(driver, xpath))
    else:
        getElement(driver, xpath).send_keys(keys)


def getChromeDriver(proxy=None):
    # return webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    options = webdriver.ChromeOptions()
    options.add_argument('start-maximized')
    options.add_argument(f'user-agent={UserAgent().get_random_user_agent()}')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if debug:
        # print("Connecting existing Chrome for debugging...")
        options.debugger_address = "127.0.0.1:9222"
    else:
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # options.add_argument('--user-data-dir=C:/Selenium1/ChromeProfile1')
    if not images:
        # print("Turning off images to save bandwidth")
        options.add_argument("--blink-settings=imagesEnabled=false")
    if headless:
        # print("Going headless")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
    if maximize:
        # print("Maximizing Chrome ")
        options.add_argument("--start-maximized")
    if proxy:
        # print(f"Adding proxy: {proxy}")
        options.add_argument(f"--proxy-server={proxy}")
    if incognito:
        # print("Going incognito")
        options.add_argument("--incognito")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def getFirefoxDriver():
    options = webdriver.FirefoxOptions()
    if not images:
        # print("Turning off images to save bandwidth")
        options.set_preference("permissions.default.image", 2)
    if incognito:
        # print("Enabling incognito mode")
        options.set_preference("browser.privatebrowsing.autostart", True)
    if headless:
        # print("Hiding Firefox")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
    return webdriver.Firefox(options)


if __name__ == '__main__':
    logo()
    driver = getChromeDriver()
    time.sleep(3)
    driver.get('https://www.google.com/search?q=autotrader.ca')
    time.sleep(1)
    click(driver, '//h3')
    time.sleep(2)
    # driver.get('https://www.autotrader.ca')
    print(driver.title)
    time.sleep(1)
    driver.get('https://www.autotrader.ca/cars')
    time.sleep(1)
    main()
