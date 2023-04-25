from googleapiclient.discovery import build
import datetime
import pytube
import cv2
import glob
from moviepy.editor import *
import shutil
from PIL import Image, ImageChops
from skimage.metrics import structural_similarity as ssim
import numpy as np

API_KEY = 'AIzaSyDARsYmVfznRro0fmY8fa3PiyKy2ZMw4cg'
PLAYLIST_ID = 'PLwtpvkURtbBZakorOTyVstInQ6AeaFAXg'
YT_LIST_TXT = "yt_list.txt"
HELP_LIST = "help_list.txt"
MUSIC_FOLDER = "music"
IMAGE_FOLDER = "compare_image_folder"

STATUS = 0
NAME = 1
VIDEO_ID = 2
DATE = 3

CONTROL = True
DEBUG = True
AUDIO = 'mp3'
VIDEO = 'mp4'

FIRST_IMAGE = "first_image.jpg"
SECOND_IMAGE = "second_image.jpg"

def compare_images(image1_path, image2_path):

    image1 = Image.open(image1_path)
    image2 = Image.open(image2_path)

    if image1.mode != image2.mode:
        return False

    # Resize images to a common size
    image1 = image1.resize((1280, 720))
    image2 = image2.resize((1280, 720))

    # Convert images to grayscale
    gray_image1 = image1.convert('L')
    gray_image2 = image2.convert('L')

    # Convert PIL images to NumPy arrays
    array1 = np.array(gray_image1)
    array2 = np.array(gray_image2)

    # Compute SSIM between two images
    ssim_value = ssim(array1, array2)

    print("SSIM between two images is:" + str(ssim_value) + " - " + str(ssim_value > 0.95))

    return ssim_value > 0.95

    """"
    #diff = ImageChops.difference(image1, image2)
    #return diff.getbbox() is None
    # Calculate mean squared error (MSE)
    mse = np.mean((np.array(image1) - np.array(image2)) ** 2)
    print("mse: " + str(mse) + " - "+ str(mse <= 25))
    return mse <= 25
    """

# https://stackoverflow.com/questions/4719438/editing-specific-line-in-text-file-in-python
def create_ifnot(filename):
    if not os.path.isfile(filename):
        with open(filename, "w") as file:
            # file.write("status|name|video_id|date")
            print(f"{filename} has been created.")
    else:
        print(f"{filename} already exists.")


def replace_line(number, line_text):
    with open(YT_LIST_TXT, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    lines[number] = line_text
    with open(YT_LIST_TXT, 'w', encoding='utf-8') as file:
        file.writelines(lines)
        file.close()
def replace_line_change(line_count,number ,newstring):
    with open(YT_LIST_TXT, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    radka = change(lines[line_count],number, newstring)
    lines[line_count] = radka
    with open(YT_LIST_TXT, 'w', encoding='utf-8') as file:
        file.writelines(lines)
        file.close()

def change( line,number, newstring):
    casti = line.split('|')
    casti[number] = newstring
    result = '|'.join(casti)
    if number == DATE:  # poslední cast
        return result + "\n"
    return result


def get_part(number, line):
    casti = line.split('|')
    return casti[number]

def name_correction(name):
    return name.replace('|', '_')
def get_list(api_key, playlist_id, yt_list_txt):
    youtube = build('youtube', 'v3', developerKey=api_key)

    # Get the first page of videos from the playlist
    request = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()

    # Get the list of videos from the response
    videos = []
    for item in response['items']:
        video = {
            'title': item['snippet']['title'],
            'video_id': item['snippet']['resourceId']['videoId']
        }
        videos.append(video)

    # If there are more pages of videos, get them
    while 'nextPageToken' in response:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=response['nextPageToken']
        )
        response = request.execute()
        for item in response['items']:
            video = {
                'title': item['snippet']['title'],
                'video_id': item['snippet']['resourceId']['videoId']
            }
            videos.append(video)
    found_int = 0
    for video in videos:
        video['title'] = name_correction(video['title'])

        found = False
        file = open(yt_list_txt, 'r', encoding='utf-8')
        radka = 0
        line_count = 0
        for line in file:
            if video['video_id'] == get_part(VIDEO_ID, line):
                found = True
                radka = line_count
                break
            line_count += 1
        file.close()
        if found:
            #if DEBUG == True: print(video['video_id'] + " is in " + yt_list_txt)
            found_int = found_int + 1
            now = datetime.datetime.now()
            replace_line_change(radka, DATE,now.strftime("%d.%m.%Y, %H:%M:%S"))
        if not found:
            #if DEBUG == True: print(video['video_id'] + " is not in " + yt_list_txt)
            f = open(yt_list_txt, "a", encoding='utf-8')
            now = datetime.datetime.now()
            print("checked" + "|"
                  + video['title']
                  + "|" + video['video_id']
                  + "|" + now.strftime("%d.%m.%Y, %H:%M:%S"),
                  file=f)
            f.close()
    if DEBUG == True: print("Found: " + str(found_int)+"/"+str(len(videos)))
    return len(videos)
def download(video_id, output_folder, format):
    try:
        yt_url = "https://www.youtube.com/watch?v="
        if DEBUG == True: print("try download " + yt_url + video_id)
        yt = pytube.YouTube(yt_url + video_id)
        stream = yt.streams.filter(file_extension=format).get_highest_resolution()
    except Exception as e:
        print("Asi, nejspíš Network issue")
        print(e)
        return False

    if stream:
        video_name = stream.default_filename
        video_name = name_correction(video_name)
        default_name, ext = os.path.splitext(video_name)
        output_file = ("{}{}." + VIDEO).format(default_name, "[" + video_id + "]")
        stream.download(output_path=output_folder, filename=output_file)
        return True
    else:
        print(format + " stream is not available for video {}".format(video_id))
        return False


def files_in_folder(substring, directory):
    try:
        files = glob.glob(os.path.join(directory, "*"))
        matching_files = [file for file in files if substring in file]
    except OSError:
        print(f"Error: Could not find directory {directory}")
        exit()
    return matching_files


def extract_images(video_path, video_name):
    try:
        if not os.path.exists(IMAGE_FOLDER):
            os.makedirs(IMAGE_FOLDER)
    except OSError:
        print('Error: Creating directory of data')
    cap = cv2.VideoCapture(video_path)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_number = int(total_frames/3)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, start_image = cap.read()

    frame_number = int(total_frames*2/3)

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, end_image = cap.read()

    cap.release()

    start_image_path = os.path.join(IMAGE_FOLDER, FIRST_IMAGE)
    end_image_path = os.path.join(IMAGE_FOLDER, SECOND_IMAGE)

    cv2.imwrite(start_image_path, start_image)
    cv2.imwrite(end_image_path, end_image)

def control_format(file, line_count, line):
    jmeno = os.path.splitext(os.path.basename(file))

    if VIDEO in jmeno[1]:
        base_name = jmeno[0]
        extract_images(file, base_name)
        #if compare_images(os.path.join(IMAGE_FOLDER, base_name + FIRST_IMAGE),os.path.join(IMAGE_FOLDER, base_name + SECOND_IMAGE)):
        if compare_images(os.path.join(IMAGE_FOLDER, FIRST_IMAGE), os.path.join(IMAGE_FOLDER, SECOND_IMAGE)):
            video = VideoFileClip(file)
            video.audio.write_audiofile(os.path.join(MUSIC_FOLDER, base_name+"."+AUDIO))
            os.remove(os.path.join(MUSIC_FOLDER, base_name+"."+VIDEO))
            if DEBUG == True:print("zapsani: " +str(line_count)+" "+line+"  "+ change( line,STATUS, "audio"))
            replace_line_change(line_count, STATUS, "audio")
        else:
            if DEBUG == True: print("zapsani: " + change( line,STATUS, "video"))
            replace_line_change(line_count, STATUS, "video")

    if AUDIO in jmeno[1]:
        if DEBUG == True:print("zapsani: " + change( line,STATUS, "audio"))
        replace_line_change(line_count, STATUS, "audio")
    now = datetime.datetime.now()
    replace_line_change(line_count, DATE, now.strftime("%d.%m.%Y, %H:%M:%S"))

def download_list(yt_list_txt, output_folder, control, videos_int):
    shutil.copyfile(yt_list_txt,HELP_LIST)
    file = open(HELP_LIST, 'r', encoding='utf-8')
    line_count = 0

    for line in file:
        if DEBUG == True: print("\033[35m"+"----------------------------------------------------------"+"\033[0m")
        video_id = get_part(VIDEO_ID, line)
        files = files_in_folder("[" + video_id + "]", output_folder)
        count = len(files)
        if count > 1:
            print("\033[31m" + "Error: " + video_id + " is there " + str(len(files)) + " times" + "\033[0m")
            #print("Error: " + video_id + " is there " + str(len(files)) + " times")
            line_count += 1
            continue
        if count == 1:
            if DEBUG == True: print("\033[34m"+"one file " +video_id+" found in " + MUSIC_FOLDER+ "\033[0m")
        if count == 0:
            print("\033[36m"+"no file " +video_id+" found in " + MUSIC_FOLDER+ "\033[0m")
            if not download(video_id, output_folder, VIDEO):
                print(video_id + "is not avaible")
                replace_line_change(line_count, STATUS, "deleted")
                now = datetime.datetime.now()
                replace_line_change(line_count, DATE, now.strftime("%d.%m.%Y, %H:%M:%S"))
                line_count += 1
                continue
        files = files_in_folder("[" + video_id + "]", output_folder)
        if CONTROL:
            control_format(files[0], line_count, line)
        line_count += 1
        if DEBUG == True: print("Progress: " + str(line_count) + "/" + str(videos_int))
    file.close()


create_ifnot(YT_LIST_TXT)
# TODO pridat aby se dala zadavat i cela adresa
# když to spadne pri convertu, vznikne nedokoncena mp4 file
# nekdy to blbe píše audio a video do yt-list (možná někde nějaký špatný line_count?) - projit poradne replace a change metody
now = datetime.datetime.now()
videos_int = get_list(API_KEY, PLAYLIST_ID, YT_LIST_TXT)
download_list(YT_LIST_TXT, MUSIC_FOLDER, CONTROL, videos_int)
