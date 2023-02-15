import json
import os.path
import time
import traceback
from datetime import datetime
from random import randint
from threading import Thread, Semaphore, Lock

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

t = 1
timeout = 10

debug = True

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
thread_count = 1
semaphore = Semaphore(thread_count)
lock = Lock()


def get(url):
    res = requests.get(url, headers=headers).text
    if "Request unsuccessful. Incapsula incident ID:" not in res:
        return res
    with lock:
        driver.get(url)
        time.sleep(1)
        while "Request unsuccessful. Incapsula incident ID:" in driver.page_source:
            print("[+] Incapsula detected")
            time.sleep(randint(10, 20))
            driver.refresh()
            time.sleep(1)
        return driver.page_source


def getData(url):
    with semaphore:
        id_ = url.split('.ca/')[1].replace('/', '_').split("?")[0]
        html = f'./html/{id_}.html'
        if os.path.isfile(f'./data/{id_}.json'):
            # print(f"[+] Already scraped {url}")
            return
        print(f"[+] Scraping {url}")
        if os.path.isfile(html):
            with open(html, 'r', encoding='utf8', errors='ignore') as f:
                r = f.read()
        else:
            r = get(url)
            with open(html, 'w', encoding='utf8', errors='ignore') as f:
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
        # with open('data.json', 'w', encoding='utf8', errors='ignore') as f:
        #     json.dump(js, f, indent=4)
        data['Title'] = soup.find('title').text.replace("\\", "").strip()
        data['Image'] = soup.find("meta", {"property": "og:image"})['content']
        data['Province'] = js['deepLinkSavedSearch']['savedSearchCriteria']['provinceAbbreviation']
        for key, val in js['hero'].items():
            if key in ['year', 'price', 'mileage']:
                data[key.title()] = int(val.replace(',', '').replace('$', '').replace('km', '').strip())
            elif key in ['make', 'model', 'trim', 'vin']:
                data[key.title()] = val.replace("\\", "").strip()
        if 'featureHighlights' in js and 'options' in js['featureHighlights']:
            data['Features'] = js['featureHighlights']['options']
        data['Specs'] = js['specifications']['specs']
        data['Hero'] = js['hero']
        # print(json.dumps(data, indent=4))
        with open(f'./data/{id_}.json', 'w', encoding='utf8', errors='ignore') as f:
            json.dump(data, f, indent=4)
        return data


def main():
    if not os.path.isdir('html'):
        os.mkdir('html')
    if not os.path.isdir('data'):
        os.mkdir('data')
    if not os.path.isdir('pages'):
        os.mkdir('pages')
    # url = 'https://www.autotrader.ca/a/bmw/7%20series/boucherville/quebec/5_54555424_20090324114217770/'
    # getData(url)
    threads = []
    for year in reversed(range(2010, 2023)):
        i = 0
        last_page = 10
        # url = f"{at}/cars/?rcp={size}&rcs={i * size}"
        while i < last_page:
            try:
                url = f"https://www.autotrader.ca/cars/?rcp={size}&rcs={i * size}&srt=35&yRng={year}%2C{year + 1}&prx=-1&loc=T7X%200A4&hprc=True&wcp=True&sts=New-Used&inMarket=advancedSearch"
                print(f"[+] Getting page {i} year {year} {url}")
                if os.path.isfile(f'./pages/{year}-{i}.html'):
                    i += 1
                    continue
                    # with open(f'./pages/{year}-{i}.html', 'r', encoding='utf8', errors='ignore') as f:
                    #     r = f.read()
                else:
                    driver.get(url)
                    time.sleep(3)
                    r = driver.page_source
                    with open(f'./pages/{year}-{i}.html', 'w', encoding='utf8', errors='ignore') as f:
                        f.write(r)
                soup = BeautifulSoup(r, 'html.parser')
                h1 = soup.find('h1')
                if not h1:
                    i += 1
                    print(f"[+] No h1 {url}")
                    continue
                print(h1.text.strip())
                last_page = int(soup.find('li', {"class": "last-page page-item"})['data-page'].strip())
                # print(f"[+] Last page {last_page}")
                print(f"[+] Page {i}/{last_page} Year {year} URL {url}")
                urls = soup.find_all('a', {"class": "result-title click"})
                while len(urls) == 0:
                    driver.get(url)
                    time.sleep(3)
                    r = driver.page_source
                with open(f'./pages/{year}-{i}.html', 'w', encoding='utf8', errors='ignore') as f:
                    f.write(r)
                soup = BeautifulSoup(r, 'html.parser')
                urls = soup.find_all('a', {"class": "result-title click", 'href': True})
                # print("[+] No more pages")
                # with open('error.html', 'w', encoding='utf8', errors='ignore') as efile:
                #     efile.write(r)
                # break
                for a in urls:
                    t = Thread(target=getData, args=(f"{at}{a['href']}",))
                    t.start()
                    threads.append(t)
                for t in threads:
                    t.join()
            except:
                traceback.print_exc()
            i += 1
    for thread in threads:
        thread.join()
    os.rmdir('pages')


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
    # options.add_argument(f'user-agent={UserAgent().get_random_user_agent()}')
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
        if os.name == 'nt':
            options.add_argument('--user-data-dir=C:/Selenium1/ChromeProfile')
        else:
            options.add_argument('--user-data-dir=/tmp/ChromeProfile1')
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
    while True:
        try:
            logo()
            driver = getChromeDriver()
            time.sleep(3)
            driver.get('https://www.google.com/search?q=autotrader.ca')
            time.sleep(1)
            # click(driver, '//h3')
            # time.sleep(2)
            # driver.get('https://www.autotrader.ca')
            print(driver.title)
            time.sleep(1)
            driver.get('https://www.autotrader.ca/cars')
            time.sleep(1)
            main()
            break
        except:
            traceback.print_exc()
