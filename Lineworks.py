from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time
import re
import requests
import urllib3
import platform
import threading
import os
from synology import searchfolder, searchfile, fileupload, file_move, file_rename
import json
from webdriver_manager.chrome import ChromeDriverManager
import csv
import chromedriver_autoinstaller
import Account

class works:

    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.driver = None
        self.botId = Account.WORKS_CONFIG['botId']
        self.channelId = Account.WORKS_CONFIG['channel']
        # 현재 API 호출 횟수
        self.__request_count = 0
        self.__threads_count = 0
        # 시작 시간
        self.__start = time.time()
        self.lock = threading.Lock()

        # 크롬 셋팅 및 크롬 창 띄우기
        webdriver_options = webdriver.ChromeOptions()
        webdriver_options.add_argument("--headless")
        webdriver_options.add_argument("--disable-gpu")
        webdriver_options.add_argument("--no-sandbox")
        webdriver_options.add_argument("--disable-dev-shm-usage")

        if platform.platform().__contains__('Windows'):
            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=webdriver_options)
        elif platform.platform().__contains__('Linux'):
            self.driver = webdriver.Chrome(chromedriver_autoinstaller.install(), options=webdriver_options)

        self.login()
        urllib3.disable_warnings()

    @property
    def request_count(self):
        return self.__request_count

    @request_count.setter
    def request_count(self, new_count):
        self.__request_count = new_count

    @property
    def start(self):
        return self.__start

    @start.setter
    def start(self, new_start):
        self.__start = new_start

    @property
    def threads_count(self):
        return self.__threads_count

    @threads_count.setter
    def threads_count(self, new_count):
        self.__threads_count = new_count

    # API 제한 기준 10시 ~ 19시 100회 제한 그 이외 200번으로 제한
    def request_standard(self):
        # 테스트
        # return 230
        now = datetime.now().hour
        if now >= 10 and now < 19:
            return 50
        else:
            return 150

    def request_count_up(self):
        self.lock.acquire()
        self.request_count = self.request_count + 1
        self.lock.release()

    def threads_count_up(self):
        self.lock.acquire()
        self.threads_count = self.threads_count + 1
        self.lock.release()

    def threads_wait(self):
        self.lock.acquire()
        if self.threads_count >= 10:
            print("Threads Limit Lock...")
            time.sleep(60)
            self.threads_count = 0
            print("Threads Limit UnLock...")
        self.lock.release()

    def api_wait(self):
        self.lock.acquire()
        if self.request_count >= self.request_standard():
            print("API Limit Lock...")
            while True:
                time.sleep(0.1)
                if (time.time() - self.start) > 60:
                    self.request_count = 0
                    self.start = time.time()
                    print("API Limit UnLock...")
                    break
        self.lock.release()

    def close(self):
        # 크롬, 드라이버 KILL
        self.driver.quit()

    def login(self):
        # 라인웍스 로그인
        print("라인웍스 로그인")

        URL = 'https://auth.worksmobile.com/oauth2/v2.0/authorize?client_id=nuWikIw3iul_p3RzulkE&redirect_uri=https://127.0.0.1&scope=mail,bot,directory,group,file,orgunit&response_type=code&state=12345678'

        self.driver.get(url=URL)

        time.sleep(1)
        id = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'inputId')))
        id.send_keys('')
        pw = self.driver.find_element_by_id('password')
        pw.send_keys('')

        pw.send_keys(Keys.ENTER)

        p = re.compile(r'(\w+\w*)==')
        m = p.search(self.driver.current_url)
        print(m.group())

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        data = {'code': m.group(), 'grant_type': 'authorization_code', 'client_id': 'nuWikIw3iul_p3RzulkE',
                'client_secret': 'dR_Q8yldhy'}

        res = requests.post('https://auth.worksmobile.com/oauth2/v2.0/token', data=data, headers=headers)

        token_json = res.json()
        self.token = token_json['access_token']
        self.driver.quit()

    def token_refresh(self):

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        data = {'refresh_token': self.refresh_token, 'grant_type': 'refresh_token', 'client_id': 'PldvLUuCLrxTeGYYCvcX',
                'client_secret': 'rZrO311VyY'}

        res = requests.post('https://auth.worksmobile.com/oauth2/v2.0/token', data=data, headers=headers)

        token_json = res.json()
        self.token = token_json['access_token']

    def orgunits(self):
        # 조직 조회
        cursor = None
        return_list = []

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        while True:
            URL = 'https://www.worksapis.com/v1.0/orgunits'

            if cursor is None:
                res = requests.get(URL, headers=headers)
                list = res.json()

                for key in list['orgUnits']:
                    return_list.append(groupfolder(key['orgUnitName'], key['orgUnitId'], None))
                cursor = list['responseMetaData']['nextCursor']

                if cursor is None:
                    return return_list
                    break

            else:
                res = requests.get(URL+"?cursor="+cursor, headers=headers)
                list = res.json()
                for key in list['orgUnits']:
                    return_list.append(groupfolder(key['orgUnitName'], key['orgUnitId'], None))

                cursor = list['responseMetaData']['nextCursor']
                if cursor is None:
                    return return_list
                    break

    def groups(self):
        # 그룹 조회
        cursor = None
        return_list = []

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        while True:
            URL = 'https://www.worksapis.com/v1.0/groups'
            if cursor is None:
                res = requests.get(URL, headers=headers)
                list = res.json()

                for key in list['groups']:
                    return_list.append(groupfolder(key['groupName'], key['groupId'], key['members']))
                    # return_list[key['groupName']] = [key['groupId'], key['members']]

                cursor = list['responseMetaData']['nextCursor']

                if cursor is None:
                    return return_list
                    break

            else:
                res = requests.get(URL+"?cursor="+cursor, headers=headers)
                list = res.json()

                for key in list['groups']:
                    return_list.append(groupfolder(key['groupName'], key['groupId'], key['members']))

                cursor = list['responseMetaData']['nextCursor']
                if cursor is None:
                    return return_list
                    break

    def groups_files(self, groupid):

        # 그룹 파일 목록 조회
        cursor = None

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        file_list = []

        while True:
            url = 'https://www.worksapis.com/v1.0/groups/{0}/folder/files'.format(groupid)

            self.api_wait()

            if cursor is None:

                res = requests.get(url, headers=headers)

                if res.status_code == 404:
                    return []
                if res.status_code == 403:
                    print(f'{res.content}')
                    log = f'{res.content}'
                    self.csv_write(log)
                    return []

                self.request_count_up()

                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. 그룹 파일 검색")
                log = f"{groupid} 그룹 파일 검색 "
                self.csv_write(log)

                if res.status_code != 403 and res.status_code != 404:
                    list = res.json()

                    try:
                        for key in list['files']:
                            file_list.append([key['filePath'], key['fileId'], key['fileType'], key['modifiedTime'],
                                              key['fileSize']])

                        cursor = list['responseMetaData']['nextCursor']
                        if cursor is None:
                            return file_list
                            break
                    except Exception as ex:
                        print(ex)

                else:
                    print(res.status_code)
                    log = f"groups_files print {res.content}"
                    # self.group_write(log)

            else:
                res = requests.get(url + "?cursor=" + cursor, headers=headers)

                self.request_count_up()

                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. 그룹 파일 검색")
                log = f"{groupid} 그룹 파일 검색"
                self.csv_write(log)

                if res.status_code != 403 and res.status_code != 404:

                    list = res.json()

                    for key in list['files']:
                        file_list.append([key['filePath'], key['fileId'], key['fileType'], key['modifiedTime'],
                                          key['fileSize']])

                    cursor = list['responseMetaData']['nextCursor']
                    if cursor is None:
                        return file_list
                        break

                else:
                    log = f"groups_files print {res.content}"
                    # self.group_write(log)


    def groups_folder_files(self, groupid, fileid):

        print("{}. 그룹 폴더 파일 검색".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        # 그룹 폴더 안 파일 목록 조회
        cursor = None

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        file_list = []

        while True:
            url = 'https://www.worksapis.com/v1.0/groups/{0}/folder/files/{1}/children'.format(groupid, fileid)

            self.api_wait()

            if cursor is None:

                    res = requests.get(url, headers=headers)

                    self.request_count_up()

                    log = f"{groupid}/{fileid} 그룹 폴더 파일 검색 "
                    self.csv_write(log)

                    list = res.json()

                    for key in list['files']:
                        file_list.append([key['filePath'], key['fileId'], key['fileType'], key['modifiedTime'],
                                          key['fileSize']])

                    cursor = list['responseMetaData']['nextCursor']

                    if cursor is None:
                        return file_list
                        break
            else:
                    res = requests.get(url + "?cursor=" + cursor, headers=headers)
                    self.request_count_up()
                    log = f"{groupid}/{fileid} 그룹 폴더 파일 검색 "
                    self.csv_write(log)

                    list = res.json()

                    for key in list['files']:
                        file_list.append([key['filePath'], key['fileId'], key['fileType'], key['modifiedTime'],
                                          key['fileSize']])

                    cursor = list['responseMetaData']['nextCursor']

                    if cursor is None:
                        return file_list
                        break

    def DownloadReqeust(self, url, filepath, mtime, works_size):

        try:
            # self.api_wait()
            folder_path = "/".join(filepath.split('/')[:len(filepath.split('/')[:-1])])
            file_name = filepath.split('/')[-1]

            # 시놀로지 file_name 맨 앞에는 .만 쓸수 없다. 치환을 해줘야 한다.
            if file_name[0] == '.' and file_name[0:2] != '..':
                file_name = '.' + file_name

            # 특수문자 제거
            if '\0x08' in file_name:
                file_name = file_name.replace('\x08', '')

            print("{0} {1} 진입".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), folder_path + "/" + file_name))

            # 폴더 생성
            # self.createFolder(os.path.dirname(os.path.realpath(__file__)) + folder_path)

            # sf = searchfile(filepath)
            sf = searchfile(folder_path + "/" + file_name)

            # 나스 파일 검색
            if sf is False:

                # 나스 폴더 검색, 없을 시에는 폴더 생성
                searchfolder(folder_path)

                # 파일 검색 없을 시 라인웍스 파일 다운로드
                print("{0} {1} 다운로드".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), folder_path + "/" + file_name))
                log = f"{folder_path}/{file_name} 다운로드"
                # self.file_write(log)

                self.download(url, folder_path, file_name)

            # 파일 있을 시 수정 날짜를 나스에 있는 파일과 용량 및 날짜 비교 한다.
            else:
                try:
                    # NAS 파일 사이즈
                    nas_file_size = sf['data']['files'][0]['additional']['size']
                    nas_time = datetime.fromtimestamp(sf['data']['files'][0]['additional']['time']['mtime'])

                    mtime = datetime.strptime(mtime[:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S')

                    # 사이즈 다를 시 백업 시작
                    if nas_file_size != works_size:

                        # 76 사이즈 == 다운로드가 안된 것 OverWrite 하여 다운로드 함
                        if nas_file_size == 76:
                            # 파일 다운로드 후 업로드
                            log = f"{folder_path}/{file_name} 다운로드"
                            # self.file_write(log)
                            self.download(url, folder_path, file_name)

                        else:
                            # Nas 폴더 생성
                            old_path = folder_path + "/" + file_name + "_OLD"

                            searchfolder(old_path)
                            # 원래 있던 NAS 파일 저장 _OLD 로 이동
                            file_move(folder_path + "/" + file_name, old_path)
                            # 파일명 변경
                            file_rename(old_path + "/" + file_name, datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                                        + "_" +file_name)

                            self.download(url, folder_path, file_name)
                            log = f"{folder_path}/{file_name} 다운로드"
                            # self.file_write(log)
                            self.request_count_up()

                    # 수정시간 다를 시 백업 시작
                    if int((nas_time - mtime).days) < -1:

                        # Nas 폴더 생성
                        old_path = folder_path + "/" + file_name + "_OLD"

                        searchfolder(old_path)
                        # 원래 있던 NAS 파일 저장 _OLD 로 이동
                        file_move(folder_path + "/" + file_name, old_path)
                        # 파일명 변경
                        file_rename(old_path + "/" + file_name, datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                                    + "_" + file_name)

                        print("수정 시간 다름")

                except Exception as ex:
                    print(ex)
                    self.file_write(f"download try inline {filepath} ex = {str(ex)}")

        except Exception as ex:
            print(ex)
            self.file_write(f"download try outline {filepath} ex = {str(ex)}")

    def download(self, url, folder_path, file_name):

        headers = {
            'Authorization': 'Bearer ' + self.token
        }

        r = requests.get(url, headers=headers)

        self.request_count_up()
        self.threads_count_up()

        log = f"{folder_path}/{file_name} 파일 다운로드 및 나스 업로드"
        self.csv_write(log)

        if r.status_code == 403:
            print(r.content)
            log = f"download 403 {str(r.content)}"
            self.csv_write(log)
            return
        elif r.status_code == 429:
            log = f"download 429 {str(r.content)}"
            self.csv_write(log)

            for i in range(0, 10):
                self.api_wait()

                if self.download(url, folder_path, file_name):
                    log = f"{folder_path}/{file_name} 파일 재 다운로드 및 나스 업로드"
                    self.csv_write(log)
                    time.sleep(1)
                    break
            # return

        f = open(os.path.dirname(os.path.realpath(__file__)) + "/data" + folder_path + "/" + file_name, 'wb')
        f.write(r.content)
        f.close()

        download_path = os.path.dirname(os.path.realpath(__file__)) + "/data" + folder_path + "/" + file_name

        # 파일 업로드
        if 'Upload Complete' not in fileupload(folder_path, download_path):
            for i in range(0, 10):
                if 'Upload Complete' not in fileupload(folder_path, download_path):

                    break
                time.sleep(1)

        # self.message(f'{folder_path} 폴더에 {file_name} 파일이 업로드 되었습니다.')

        # 컴퓨터 상 파일 삭제
        try:
            os.remove(download_path)
        except FileNotFoundError:
            None
            # print("삭제 완료")
        return True

    def permissons(self, groupid, members):

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        url = 'https://www.worksapis.com/v1.0/groups/{0}'.format(groupid)

        payload = json.dumps({
            "members": members
        })

        r = requests.patch(url, headers=headers, data=payload)

    def createFolder(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            None
            # print('Error Creating directory. ' + directory)

    def csv_write(self, text):
        with open('log.csv', 'a', encoding='utf-8') as f:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            wr = csv.writer(f)
            wr.writerow([now + " " + text + "Request_count = " + str(self.request_count)])

    def group_write(self, text):
        with open('group.csv', 'a', encoding='utf-8') as f:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            wr = csv.writer(f)
            wr.writerow([now + " " + text])

    def file_write(self, text):
        with open('group.csv', 'a', encoding='utf-8') as f:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            wr = csv.writer(f)
            wr.writerow([now + " " + text])

    def message(self, text):
        URL = f'https://www.worksapis.com/v1.0/bots/{self.botId}/channels/{self.channelId}/messages'

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        data = {
            "content": {
                "type": "text",
                "text": text
            }
        }

        requests.post(url=URL, json=data, headers=headers)
        self.request_count_up()

class groupfolder:

    def __init__(self, name, id, member=None):
        self.name = name
        self.id = id
        self.member = None if member is None else member
