import socket
import ssl
import logging
import json
import requests
import re
import datetime
import time
from os import path


BNICK = 'YT-Info-2'
BIDENT = 'YT-Info'
BNAME = 'YT-Info'
BSERVER = 'irc.rizon.net'
BPORT = '+6697'

API_KEY = "Your-API-Key"

ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False

logging.basicConfig(level=logging.DEBUG,
                    filename='irc.log',
                    filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up logging to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


def decode(bytes):
    try: 
        text = bytes.decode('utf-8')
    except UnicodeDecodeError:
        try: 
            text = bytes.decode('latin1')
        except UnicodeDecodeError:
            try: 
                text = bytes.decode('iso-8859-1')
            except UnicodeDecodeError:
                text = bytes.decode('cp1252')
    return text


def ircsend(msg):
    if msg != '':
        ircsock.send(bytes(f'{msg}\r\n','UTF-8'))

message_throttle = 5 # messages can be sent every 5 seconds
last_message_time = 0

def send_message(message):
    global last_message_time
    current_time = time.time()
    if current_time - last_message_time > message_throttle:
        ircsend(message)
        last_message_time = current_time
    else:
        print("Throttling: message not sent.")

def connect():
    global ircsock
    global connected
    global BPORT
    global BSERVER
    global BNICK
    global BIDENT
    global BNAME

    if str(BPORT)[:1] == '+':
        ircsock = ssl.wrap_socket(ircsock)
        BPORT = int(BPORT[1:])
    else:
        BPORT = int(BPORT)

    ircsock.connect_ex((BSERVER, BPORT))
    ircsend(f'NICK {BNICK}')
    ircsend(f'USER {BIDENT} * * :{BNAME}')


def save_channel(channel):
    with open('channels.txt', 'a') as f:
        f.write(channel + '\n')


def join_saved_channels():
    if not path.exists('channels.txt'):
        with open('channels.txt', 'w') as f:
            pass  # create the file if it does not exist
    else:
        with open('channels.txt', 'r') as f:
            channels = f.readlines()
            for channel in channels:
                ircsend(f'JOIN {channel.strip()}')
                print(f'JOIN {channel.strip()}')


def search_youtube(query):
    url = f'https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={API_KEY}'
    response = requests.get(url)
    data = json.loads(response.text)
    if 'items' in data:
        video_id = data['items'][0]['id']['videoId']
        title = data['items'][0]['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_statistics_url = f'https://www.googleapis.com/youtube/v3/videos?part=statistics,contentDetails&id={video_id}&key={API_KEY}'
        response = requests.get(video_statistics_url)
        data = json.loads(response.text)
        if 'items' in data:
            view_count = format(int(data['items'][0]['statistics']['viewCount']), ",")
            duration_str = data['items'][0]['contentDetails']['duration']
            duration_match = re.search(r"(\d+)M(\d+)S", duration_str)
            if duration_match:
                duration = datetime.timedelta(minutes=int(duration_match.group(1)), seconds=int(duration_match.group(2)))
                return f"Title: {title} - {video_url} - Views: {view_count} - Duration: {duration}"
            else:
                return "No results found."
        else:
            return "No results found."
    else:
        return "No results found."


def main():
    global connected
    if not connected:
        connect()
        connected = True

    while connected:
        recvText = ircsock.recv(2048)
        ircmsg = decode(recvText)
        line = ircmsg.strip('\n\r')
        if ircmsg.find('PRIVMSG') != -1:
            channel = ircmsg.split(' ')[2]
        logging.info(line)
        print(line)

        if ircmsg.find('PING') != -1:
            nospoof = ircmsg.split(' ', 1)[1]
            ircsend("PONG " + nospoof)

        if ircmsg.find(f'INVITE {BNICK} :') != -1:
            channel = line.split(' ')[3]
            ircsend(f'JOIN {channel}')
            save_channel(channel)

        if ircmsg.find(f' 001 {BNICK} :') != -1:
            join_saved_channels()

        if "!yt" in line:
            channel = line.split(" ")[2]
            match = re.search("!yt (.*)", line)
            query = match.group(1)
            result = search_youtube(query)
            ircsend(f'PRIVMSG {channel} :{result}')

        youtube_urls = re.finditer("(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([\w-]{11})", line)
        for match in youtube_urls:
            video_id = match.group(1)
            result = search_youtube(video_id)
            ircsend(f'PRIVMSG {channel} :{result}')


main()
