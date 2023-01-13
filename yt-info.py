import re
import socket
import json
import requests

# YouTube API key
API_KEY = "AIzaSyBFIemVpxbkMMlfUcKtXQvLGR7TjUVeMQE"

# Connect to the IRC server
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = "irc.rizon.net"
channel = "##ct"
botnick = "youtubebot"
irc.connect((server, 6667))
irc.send(f"NICK {botnick}\n".encode())
irc.send(f"USER {botnick} {botnick} {botnick} :This is a test bot\n".encode())

# Read channels from file on startup
try:
    with open('channels.txt', 'r') as f:
        channels = f.readlines()
    channels = [c.strip() for c in channels]
except FileNotFoundError:
        channels = []

# Continuously read messages from the server
while True:
    ircmsg = irc.recv(2048).decode()
    print(ircmsg)
    if ircmsg.find("PING :") != -1:
        if ircmsg.find(f"376 {botnick}") != -1:
            for channel in channels:
            irc.send(f"JOIN {channel}\n".encode())
        ping = ircmsg.split(":")[-1]
        irc.send(f"PONG :{ping}\n".encode())

    # Check for INVITE command
    if ircmsg.find("INVITE") != -1:
        channel = ircmsg.split(" ")[1]
        irc.send(f"JOIN {channel}\n".encode())
        channels.append(channel)
        with open('channels.txt', 'w') as f:
            for c in channels:
                f.write("%s\n" % c)

    # Check for !yt command
    if ircmsg.find("!yt") != -1:
        query = ircmsg.split("!yt ")[1]
        query = query.strip()
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={API_KEY}"
        response = requests.get(url)
        data = json.loads(response.text)
        video = data["items"][0]
        title = video["snippet"]["title"]
        link = f"https://www.youtube.com/watch?v={video['id']['videoId']}"
        channel_name = ircmsg.split(' PRIVMSG ')[-1].split(' :')[0]
        irc.send(f"PRIVMSG {channel_name} :{title} - {link}\n".encode())
    # Check for YouTube URLs in all channels
    if ' PRIVMSG ' in ircmsg:
        youtube_url = re.findall('(https?://www\.youtube\.com/watch\S+)', ircmsg)
        if youtube_url:
            youtube_id = youtube_url[0].split("=")[-1]
            url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={youtube_id}&key={API_KEY}"
            response = requests.get(url)
            data = json.loads(response.text)
            video_title = data['items'][0]['snippet']['title']
            channel_name = ircmsg.split(' PRIVMSG ')[-1].split(' :')[0]
            irc.send(f"PRIVMSG {channel_name} :The title of the video is: {video_title}\n".encode())
