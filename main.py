import Lineworks
import time
import threading
from queue import Queue
import psutil

def use_mem():
    memory_usage_dict = dict(psutil.virtual_memory()._asdict())
    memory_usage_percent = memory_usage_dict['percent']
    return memory_usage_percent

def list_chunk(lst, n):
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def list_chunk2(list, n, m):
    if m > 10:
        list2 = list_chunk(list[:m], 10)
    else:
        list2 = [list[:m]]

    for i in range(m, len(list), n):
        list2.append(list[i:i+n])

    return list2

def pop(q):

    while True:
        info = q.get()

        if info:
            lw.api_wait()

            if use_mem() > 80:
                while True:
                    if use_mem() <= 70:
                        break
                    time.sleep(1)

            thread = threading.Thread(target=lw.DownloadReqeust,
                                      args=(f'https://kr1-file.drive.worksmobile.com/drive/v3/groups/'
                                            f'{info["groupid"]}/files/{info["file"][1]}''?auth=openapi',
                                            info["file"][0], info["file"][3], info["file"][4]))
            thread.start()
            lw.threads_count_up()
            if lw.threads_count >= 5:
                thread.join()
                lw.threads_count = 0

# request_list = ['대공님에게 빠져버렸습니다',
# '원래 악녀가 체질',
# '내 남편은 뱀파이어',
# '대표님의 전속노예가 되었습니다']

while True:
    # LineWorks 셋팅 및 로그인
    lw = Lineworks.works()

    # 조직 및 그룹 가져오기
    list = lw.orgunits()
    list.extend(lw.groups())

    # Queue 실행
    queue = Queue()
    thread1 = threading.Thread(target=pop, args=(queue,))

    thread1.start()

    threads_count = 0

    start = True

    for orgunits in list:


        # if '결혼부터' in orgunits.name and start is False:
        #     start = True
        #     continue

        # if len([x for x in request_list if x in orgunits.name]) == 0:
        #     continue

        if start:

            # 권한 체크
            # 루트 파일 리스트 가져옴
            root_list = lw.groups_files(orgunits.id)
            # 시작 시간
            lw.start = time.time()
            # minimal size list
            file_list = []

            # 폴더 리스트 가져오기
            for item in root_list:

                if item[2] == 'FOLDER':
                    # TimeOut Error is Retry
                    try:
                        result = lw.groups_folder_files(orgunits.id, item[1])

                    except Exception as ex:
                        log = f"groups_folder_files print request Error ReTry"
                        print(ex)
                        lw.group_write(log + " " + str(ex))

                        for i in range(1, 10):
                            time.sleep(2)
                            try:
                                result = lw.groups_folder_files(orgunits.id, item[1])
                                break
                            except Exception as ex:
                                log = f"groups_folder_files print request Retry Error"
                                print(ex)
                                lw.group_write(log + " " + str(ex))
                                continue

                    time.sleep(0.1)
                    temp_list = result

                    for temp in temp_list:
                        if temp[2] == 'FOLDER':
                            root_list.extend([temp])
                        else:
                            # Queue put
                            if (temp[4] / 1000000) > 150:
                                queue.put({'groupid': orgunits.id, 'file': temp})
                            else:
                                file_list.append(temp)
                else:
                    # Queue put
                    if (item[4] / 1000000) > 150:
                        queue.put({'groupid': orgunits.id, 'file': item})
                    else:
                        file_list.append(item)

            # 큐 끝나길 기다리기
            if not queue.empty():
                while True:
                    if queue.empty():
                        break
                    time.sleep(1)

            # 50MB 이하 병렬 다운로드
            lst = list_chunk2(file_list, 10, lw.request_standard() - lw.request_count)

            for list in lst:

                lw.api_wait()

                threads = [threading.Thread(target=lw.DownloadReqeust,
                                            args=(f'https://kr1-file.drive.worksmobile.com/drive/v3/groups/'
                                                  f'{orgunits.id}/files/{info[1]}''?auth=openapi', info[0], info[3],
                                                  info[4])) for info in list]
                for item in threads:
                    item.start()

                for item in threads:
                    item.join()

            lw.message(f"{orgunits.name} 동기화 완료 하였습니다.")

    print('End')


