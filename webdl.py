import os
import json
import subprocess
import argparse
import sys
import pyfiglet
from rich import print
from typing import DefaultDict

title = pyfiglet.figlet_format('WEBDL Script', font='slant')
print(f'[yellow]{title}[/yellow]')
print("by parnex Edited By JudgeU")
print("Required files : mkvmerge.exe, XstreamDL-CLI, mp4decrypt.exe, ffmpeg.exe, aria2c.exe, ccextractorwinfull.exe\n")

arguments = argparse.ArgumentParser()
# arguments.add_argument("-m", "--video-link", dest="mpd", help="MPD url")
arguments.add_argument("-o", '--output', dest="output", help="Specify output file name with no extension", required=True)
arguments.add_argument("-id", dest="id", action='store_true', help="use if you want to manually enter video and audio id.")
args = arguments.parse_args()

with open("keys.json") as json_data:
    config = json.load(json_data)
    json_mpd_url = config[0]['mpd_url']
    try:
        keys = ""
        for i in range(1, len(config)):
            keys += f"--key {config[i]['kid']}:{config[i]['hex_key']} "
    except:
        keys = ""
        for i in range(1, len(config)-1):
            keys += f"--key {config[i]['kid']}:{config[i]['hex_key']} "

currentFile = __file__
realPath = os.path.realpath(currentFile)
dirPath = os.path.dirname(realPath)
dirName = os.path.basename(dirPath)

ccextractorwinfullexe = dirPath + '/binaries/ccextractorwinfull.exe'
aria2cexe = dirPath + '/binaries/aria2c.exe'
mp4decryptexe = dirPath + '/binaries/mp4decrypt_new.exe'
mkvmergeexe = dirPath + '/binaries/mkvmerge.exe'
XstreamDLexe = dirPath + '/binaries/XstreamDL-CLI.exe'

# mpdurl = str(args.mpd)
output = str(args.output)


print(f'Selected MPD : {json_mpd_url}\n')
subprocess.run([XstreamDLexe, json_mpd_url, '--select', '-name', 'encrypted', '-save-dir', dirPath, '--enable-auto-delete', '--limit-per-host', '100', '--mp4decrypt', 'binaries', '--ffmpeg', 'binaries'])


for filename in os.listdir("."):
   if filename.startswith("encrypted_audio"):
      os.rename(filename, "encrypted_audio.mp4")
   if filename.startswith("encrypted_video"):
      os.rename(filename, "encrypted_video.mp4")
   


print("\nDecrypting .....")
subprocess.run(f'{mp4decryptexe} --show-progress {keys} encrypted_audio.mp4 decrypted(Audio).mp4', shell=True)
subprocess.run(f'{mp4decryptexe} --show-progress {keys} encrypted_video.mp4 decrypted.mp4', shell=True)  


subprocess.run(f'{ccextractorwinfullexe} decrypted.mp4', shell=True)
os.system('ren *.srt en.srt')
print("Merging .....")
subprocess.run([mkvmergeexe, '--ui-language' ,'en', '--output', output +'.mkv', '--language', '0:eng', '--default-track', '0:yes', '--compression', '0:none', 'decrypted.mp4', '--language', '0:eng', '--default-track', '0:yes', '--compression' ,'0:none', 'decrypted(Audio).mp4','--language', '0:eng','--track-order', '0:0,1:0,2:0,3:0,4:0', 'en.srt'])
print("\nAll Done .....")


print("\nDo you want to delete the Encrypted Files : Press 1 for yes , 2 for no")
delete_choice = int(input("Enter Response : "))

if delete_choice == 1:
    os.remove("encrypted_audio.mp4")
    os.remove("encrypted_video.mp4")
    os.remove("decrypted(Audio).mp4")
    os.remove("decrypted.mp4")
    try:    
        os.remove("en.srt")
    except:
        pass
else:
    pass
