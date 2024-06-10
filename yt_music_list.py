from googleapiclient.discovery import build
import datetime
import pytube
import cv2
import glob
from moviepy.editor import *
import shutil
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import numpy as np
import argparse

API_KEY = 'AIzaSyDARsYmVfznRro0fmY8fa3PiyKy2ZMw4cg'
PLAYLIST_ID = 'PLwtpvkURtbBZakorOTyVstInQ6AeaFAXg'
LOG_FILE = "log_list.txt"
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

def print_d(msg):
    print(msg) if DEBUG else None

def compare_images(image1_path, image2_path):
    image1 = Image.open(image1_path)
    image2 = Image.open(image2_path)

    if image1.mode != image2.mode:
        return False

    image1 = image1.resize((1280, 720))
    image2 = image2.resize((1280, 720))

    gray_image1 = image1.convert('L')
    gray_image2 = image2.convert('L')

    array1 = np.array(gray_image1)
    array2 = np.array(gray_image2)

    ssim_value, _ = ssim(array1, array2, full=True)

    print(f"SSIM between two images is: {ssim_value:.4f} - {'Similar' if ssim_value >  0.95 else 'Not Similar'}")

    return ssim_value > 0.95


def create_if_not_exists(filename):
    if not os.path.isfile(filename):
        with open(filename, "w"):
            print(f"{filename} has been created.")
    else:
        print(f"{filename} already exists.")


def replace_line(number, line_text):
    with open(LOG_FILE, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    lines[number] = line_text
    with open(LOG_FILE, 'w', encoding='utf-8') as file:
        file.writelines(lines)
        file.close()


def replace_line_change(line_count, number, new_string):
    with open(LOG_FILE, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    lines[line_count] = change(lines[line_count], number, new_string)
    with open(LOG_FILE, 'w', encoding='utf-8') as file:
        file.writelines(lines)
        file.close()


def change(line, number, newstring):
    casti = line.split('|')
    casti[number] = newstring
    result = '|'.join(casti)
    return f"{result}\n" if number == DATE else result


def get_part(number, line):
    return line.split('|')[number]


def name_correction(name):
    return name.replace('|', '_')


def get_list(api_key, playlist_id, yt_list_txt):
    youtube = build('youtube', 'v3', developerKey=api_key)

    videos = []
    pageToken=None
    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=pageToken
        )

        response = request.execute()

        for item in response['items']:
            video = {
                'title': name_correction(item['snippet']['title']),
                'video_id': item['snippet']['resourceId']['videoId']
            }
            videos.append(video)

        if not response.get('nextPageToken'):
            break
        pageToken = response['nextPageToken']

    with open(yt_list_txt, 'r', encoding='utf-8') as file:
        existing_lines = file.readlines()

    existing_videos = {get_part(VIDEO_ID, line): (line_num, line) for line_num, line in enumerate(existing_lines)}

    found_count = 0
    for video in videos:
        video_id = video['video_id']
        now_str = datetime.datetime.now().strftime("%d.%m.%Y, %H:%M:%S")

        if video_id in existing_videos:
            print_d(f"{video['video_id']} is in {yt_list_txt}")
            line_num, line = existing_videos[video_id]
            found_count += 1
            replace_line_change(line_num, DATE, now_str)
        else:
            print_d(f"{video['video_id']} is not in {yt_list_txt}")
            with open(yt_list_txt, 'a', encoding='utf-8') as file:
                file.write(f"checked|{video['title']}|{video['video_id']}|{now_str}")
    print_d(f"Found:{found_count}/{len(videos)}")
    return len(videos)


def download(video_id, output_folder, format):
    try:
        yt_url = f"https://www.youtube.com/watch?v={video_id}"
        print_d(f"try download {yt_url}")
        yt = pytube.YouTube(f"{yt_url}")
        stream = yt.streams.filter(file_extension=format).get_highest_resolution()
    except Exception as e:
        print("Asi, nejspíš Network issue")
        print(e)
        return False

    if stream:
        video_name = stream.default_filename
        video_name = name_correction(video_name)
        default_name, ext = os.path.splitext(video_name)
        output_file = f"{default_name}[{video_id}].{VIDEO}"
        stream.download(output_path=output_folder, filename=output_file)
        return True
    else:
        print_d(f"{format} stream is not available for video {video_id}")
        return False


def files_in_folder(substring, directory):
    try:
        files = glob.glob(os.path.join(directory, "*"))
        matching_files = [file for file in files if substring in file]
    except OSError:
        print(f"Error: Could not find directory {directory}")
        exit()
    return matching_files


def extract_images(video_path):
    os.makedirs(IMAGE_FOLDER, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video file {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def save_frame_at_position(position, image_path):
        cap.set(cv2.CAP_PROP_POS_FRAMES, position)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(image_path, frame)
        else:
            print(f"Error: Cannot read frame at position {position}")

    start_image_path = os.path.join(IMAGE_FOLDER, FIRST_IMAGE)
    save_frame_at_position(total_frames // 3, start_image_path)

    end_image_path = os.path.join(IMAGE_FOLDER, SECOND_IMAGE)
    save_frame_at_position((total_frames * 2) // 3, end_image_path)


def control_format(file, line_count, line):
    jmeno = os.path.splitext(os.path.basename(file))

    if VIDEO in jmeno[1]:
        base_name = jmeno[0]
        extract_images(file)
        #if compare_images(os.path.join(IMAGE_FOLDER, base_name + FIRST_IMAGE),os.path.join(IMAGE_FOLDER, base_name + SECOND_IMAGE)):
        if compare_images(os.path.join(IMAGE_FOLDER, FIRST_IMAGE), os.path.join(IMAGE_FOLDER, SECOND_IMAGE)):
            video = VideoFileClip(file)
            video.audio.write_audiofile(os.path.join(MUSIC_FOLDER, f"{base_name}.{AUDIO}"))
            os.remove(os.path.join(MUSIC_FOLDER, base_name + "." + VIDEO))
            print_d(f"zapsani: {line_count} {line}  {change(line, STATUS, "audio")}")
            replace_line_change(line_count, STATUS, "audio")
        else:
            print_d(f"zapsani: {change(line, STATUS, "video")}")
            replace_line_change(line_count, STATUS, "video")

    if AUDIO in jmeno[1]:
        print_d(f"zapsani: {change(line, STATUS, "audio")}")
        replace_line_change(line_count, STATUS, "audio")
    now = datetime.datetime.now()
    replace_line_change(line_count, DATE, now.strftime("%d.%m.%Y, %H:%M:%S"))


def download_list(yt_list_txt, output_folder, videos_int):
    shutil.copyfile(yt_list_txt, HELP_LIST)
    line_count = 0
    with open(HELP_LIST, 'r', encoding='utf-8') as file:
        print(file)
        for line in file:
            print_d("\033[35m----------------------------------------------------------\033[0m")
            video_id = get_part(VIDEO_ID, line)
            files = files_in_folder(f"[{video_id}]", output_folder)
            count = len(files)
            if count > 1:
                print(f"\033[31mError: {video_id} is there {count} times\033[0m")
                line_count += 1
                continue
            if count == 1:
                print_d(f"\033[34mone file {video_id} found in {MUSIC_FOLDER}\033[0m")
            if count == 0:
                print_d(f"\033[36mno file {video_id} found in {MUSIC_FOLDER}\033[0m")
                if not download(video_id, output_folder, VIDEO):
                    print(f"{video_id} is not avaible")
                    replace_line_change(line_count, STATUS, "deleted")
                    now = datetime.datetime.now()
                    replace_line_change(line_count, DATE, now.strftime("%d.%m.%Y, %H:%M:%S"))
                    line_count += 1
                    continue
            files = files_in_folder("[" + video_id + "]", output_folder)
            if CONTROL:
                control_format(files[0], line_count, line)
            line_count += 1
            print_d(f"Progress: {line_count}/{videos_int}")


def tldr():
    print("\033[35m----------------------------------------------------------\033[0m")
    print("Example: python3 yt_music_list.py -debug 1 -control False -output music_folder ")  #TODO dodelat
    print("\033[35m----------------------------------------------------------\033[0m")
    print("Empty arguments will be supplemented from config.txt" + "Nedodelane")  #TODO a dat tam i nastaveni pro stahovani
    print("\033[35m----------------------------------------------------------\033[0m")

def config():
    parser = argparse.ArgumentParser()
    parser.add_argument("-help", action="store_true")
    parser.add_argument("--tldr", action="store_true")
    parser.add_argument("--yt_list", help="id or link of youtube list")
    parser.add_argument("--log_list", help="log list of downloaded")
    parser.add_argument("--control", help="control mp4 of already downloaded ?", default=False)
    parser.add_argument("--debug", help="see more than errors", default=False)
    parser.add_argument("--output", help="output music folder")

    global CONTROL, DEBUG, PLAYLIST_ID, MUSIC_FOLDER, LOG_FILE

    args = parser.parse_args()
    if args.help:
        parser.print_help()
        sys.exit()
    if args.tldr:
        tldr()
        sys.exit()
    CONTROL = args.control
    DEBUG = args.debug
    if args.yt_list:
        print(args.yt_list)
        exit(42)
    if args.output:
        MUSIC_FOLDER = args.output
    if args.log_list:
        LOG_FILE = args.log_list

    print(f"YTList: {PLAYLIST_ID}")
    print(f"LogList: {LOG_FILE}")
    print(f"Control: {CONTROL}")
    print(f"Output: {MUSIC_FOLDER}")
    print(f"Debug: {DEBUG}")
    print(f"Api key: {API_KEY}")


# když to spadne pri convertu, vznikne nedokoncena mp4 file
# nekdy to blbe píše audio a video do yt-list (možná někde nějaký špatný line_count?) - projit poradne replace a change metody
if __name__ == "__main__":
    config()
    create_if_not_exists(LOG_FILE)
    videos_int = get_list(API_KEY, PLAYLIST_ID, LOG_FILE)
    download_list(LOG_FILE, MUSIC_FOLDER, videos_int)
