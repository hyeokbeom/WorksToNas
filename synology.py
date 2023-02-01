import time
import os
from synology_api import filestation

fl = filestation.FileStation('nas.vbros.team', '443', 'vbrosteam', 'Qlqmfhtmxla23@#', secure=True, cert_verify=True, dsm_version=7, debug=True, otp_code=None)

def searchfolder(path):
    try:
        result = fl.get_file_list(path)
    except:
        for i in range(0, 10):
            try:
                result = fl.get_file_list(path)
                break
            except:
                continue
            time.sleep(1)

    if 'error' in result:
        # 로컬 폴더 생성
        createFolder(path)
        # NAS 폴더 생성
        createfolder(path)

def searchfile(path):
        try:
            result = fl.get_file_info('/LineWorks'+path)
        except:
            for i in range(0, 10):
                try:
                    result = fl.get_file_info('/LineWorks' + path)
                    break
                except:
                    continue
                time.sleep(1)

        if 'additional' in result['data']['files'][0]:
            return result
        else:
            return False

def createfolder(path):
    folder_path = '/LineWorks/' + '/'.join(path.split('/')[1:-1])
    folder_name = path.split('/')[-1]
    fl.create_folder(folder_path=folder_path, name=folder_name)

def createFolder(directory):
    try:
        if not os.path.exists(os.path.dirname(os.path.realpath(__file__)) + "/data" + directory):
            os.makedirs(os.path.dirname(os.path.realpath(__file__)) + "/data" + directory)
    except OSError:
        None
        # print('Error Creating directory. ' + directory)

def fileupload(path, file_path):
    path = '/LineWorks' + path
    return fl.upload_file(dest_path=path, file_path=file_path, overwrite=True)

    # fl.start_copy_move()

def file_move(path, dest):
    path = '/LineWorks' + path
    dest = '/LineWorks' + dest

    fl.start_copy_move(path=path, dest_folder_path=dest)

def file_remove():
    fl.start

def file_rename(path, name):
    path = '/LineWorks' + path
    fl.rename_folder(path, name)
# fl.start_copy_move(path='/nas2/test/test.txt', dest_folder_path='/nas2/test2')

