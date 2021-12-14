import os
import json
import subprocess
import argparse
import sys
import pyfiglet
from rich import print
from typing import DefaultDict

import base64, requests, xmltodict
from base64 import b64encode
import headers
# import cookies
from decrypt.cdm import cdm, deviceconfig
from decrypt.wvdecryptcustom import WvDecrypt
from decrypt.cdm.formats import wv_proto2_pb2 as wv_proto2
import logging
# logging.basicConfig(level=logging.DEBUG)

title = pyfiglet.figlet_format('WEBDL Script', font='slant')
print(f'[magenta]{title}[/magenta]')
print("by parnex")
print("Required files : yt-dlp.exe, mkvmerge.exe, mp4decrypt.exe, aria2c.exe\n")

arguments = argparse.ArgumentParser()
# arguments.add_argument("-m", "--video-link", dest="mpd", help="MPD url")
arguments.add_argument("-o", '--output', dest="output", help="Specify output file name with no extension", required=True)
arguments.add_argument("-id", dest="id", action='store_true', help="use if you want to manually enter video and audio id.")
arguments.add_argument("-s", dest="subtitle", help="enter subtitle url")
args = arguments.parse_args()

currentFile = __file__
realPath = os.path.realpath(currentFile)
dirPath = os.path.dirname(realPath)
dirName = os.path.basename(dirPath)

youtubedlexe = dirPath + '/binaries/yt-dlp.exe'
aria2cexe = dirPath + '/binaries/aria2c.exe'
mp4decryptexe = dirPath + '/binaries/mp4decrypt_new.exe'
mkvmergeexe = dirPath + '/binaries/mkvmerge.exe'
SubtitleEditexe = dirPath + '/binaries/SubtitleEdit.exe'

# mpdurl = str(args.mpd)
output = str(args.output)
subtitle = str(args.subtitle)


def get_pssh(mpd_url):
    r = requests.get(url=mpd_url)
    r.raise_for_status()
    xml = xmltodict.parse(r.text)
    mpd = json.loads(json.dumps(xml))
    tracks = mpd['MPD']['Period']['AdaptationSet']
    for video_tracks in tracks:
        if video_tracks['@mimeType'] == 'video/mp4':
            try:
                for t in video_tracks['ContentProtection']:
                    if t['@schemeIdUri'].lower() == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                        pssh = t["cenc:pssh"]
            except KeyError:
                for t in video_tracks['Representation'][0]['ContentProtection']:
                    if t['@schemeIdUri'].lower() == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                        pssh = t["cenc:pssh"]['#text']
            except TypeError:
                pssh = input('Unable to find PSSH in mpd. Edit getPSSH.py or enter PSSH manually: ')        
    return pssh
    
    
mpd_url = input('\nInput MPD URL: ')
lic_url = input('License URL: ')
# hardcoded for kinopoisk.ru
# lic_url = 'https://widevine-proxy.ott.yandex.ru/proxy'

pssh = get_pssh(mpd_url)

# params from mdp_url:
# ottsession=5945048d6f844d1699054cc5d44548f1&
# puid=339572866&
# video_content_id=4315082489d87677b21f7c83593fcb73&

print(f'{chr(10)}PSSH obtained.\n{pssh}')



def WV_Function(pssh, lic_url, cert_b64=None):
	"""main func, emulates license request and then decrypt obtained license
	fileds that changes every new request is signature, expirationTimestamp, watchSessionId, puid, and rawLicenseRequestBase64 """
	wvdecrypt = WvDecrypt(init_data_b64=pssh, cert_data_b64=cert_b64, device=deviceconfig.device_android_generic)                   
	response = requests.post(url=lic_url, headers=headers.headers, data=wvdecrypt.get_challenge())
	if response.status_code == 200:
		widevine_license = response
	elif response.status_code != 200:
		request = b64encode(wvdecrypt.get_challenge())
		response = requests.post(url=lic_url, headers=headers.headers,
		json={
		"rawLicenseRequestBase64": str(request, "utf-8" ), 
		})
		if response.status_code == 200:
			widevine_license = response
		else:
			request = b64encode(wvdecrypt.get_challenge())
			signature = cdm.hash_object
			widevine_license = requests.post(url=lic_url, headers=headers.headers,
			json={
			"rawLicenseRequestBase64": str(request, "utf-8" ), 
			"puid": 				'339572866',
			"watchSessionId": 		'ed0e355063ac48b783130a390dc27ba6',
			"contentId": 			'4315082489d87677b21f7c83593fcb73',
			"contentTypeId": 		'21',
			"serviceName": 			'ott-kp',
			"productId": 			'2',
			"monetizationModel": 	'SVOD',
			"expirationTimestamp": 	'1639009453',
			"verificationRequired": 'false',
			"signature": 			str(signature), 
			# "signature":'b6ca3161c8bd38105e87770458aee16191214cfa', That is fucking amazon aws signing protocol!! V4!!
			"version":				'V4'
			})	
	
	print(f'{chr(10)}license response status: {widevine_license}{chr(10)}')
	if widevine_license.status_code != 200:
		print(f'server did not issue license, check json params in POST request.{chr(10)}')

	try: 
		license_b64 = b64encode(widevine_license.content)
	except TypeError:
		license_b64 = json.loads(widevine_license.content.decode())['license']

	wvdecrypt.update_license(license_b64)
	Correct, keyswvdecrypt = wvdecrypt.start_process()
	if Correct:
		return Correct, keyswvdecrypt   
correct, keys = WV_Function(pssh, lic_url)


try:
    os.remove("keys.txt")
except:
    pass


for key in keys:
    print('KID:KEY -> ' + key)
    with open('keys.txt', 'a+', encoding='utf8') as (file):
        file.write(key + '\n')

if args.id:
    print(f'Selected MPD : {mpd_url}\n')    
    subprocess.run([youtubedlexe, '-k', '--allow-unplayable-formats', '--no-check-certificate', '-F', mpd_url])

    vid_id = input("\nEnter Video ID : ")
    audio_id = input("Enter Audio ID : ")
    subprocess.run([youtubedlexe, '-k', '--allow-unplayable-formats', '--no-check-certificate', '-f', audio_id, '--fixup', 'never', mpd_url, '-o', 'encrypted.m4a', '--external-downloader', aria2cexe, '--external-downloader-args', '-x 16 -s 16 -k 1M'])
    subprocess.run([youtubedlexe, '-k', '--allow-unplayable-formats', '--no-check-certificate', '-f', vid_id, '--fixup', 'never', mpd_url, '-o', 'encrypted.mp4', '--external-downloader', aria2cexe, '--external-downloader-args', '-x 16 -s 16 -k 1M'])   

else:
    print(f'Selected MPD : {mpd_url}\n')
    subprocess.run([youtubedlexe, '-k', '--allow-unplayable-formats', '--no-check-certificate', '-f', 'ba', '--fixup', 'never', mpd_url, '-o', 'encrypted.m4a', '--external-downloader', aria2cexe, '--external-downloader-args', '-x 16 -s 16 -k 1M'])
    subprocess.run([youtubedlexe, '-k', '--allow-unplayable-formats', '--no-check-certificate', '-f', 'bv', '--fixup', 'never', mpd_url, '-o', 'encrypted.mp4', '--external-downloader', aria2cexe, '--external-downloader-args', '-x 16 -s 16 -k 1M'])    

with open("keys.txt", 'r') as f:
    file = f.readlines()

length = len(file)
for x in str(length):
    keys = ""
    for i in range(0, length):
        key = file[i][33 : 65]
        kid = file[i][0 : 32]
        keys += f'--key {kid}:{key} '

print("\nDecrypting .....")
subprocess.run(f'{mp4decryptexe} --show-progress {keys} encrypted.m4a decrypted.m4a', shell=True)
subprocess.run(f'{mp4decryptexe} --show-progress {keys} encrypted.mp4 decrypted.mp4', shell=True)  

if args.subtitle:
    subprocess.run(f'{aria2cexe} {subtitle}', shell=True)
    os.system('ren *.xml en.xml')
    subprocess.run(f'{SubtitleEditexe} /convert en.xml srt', shell=True) 
    print("Merging .....")
    subprocess.run([mkvmergeexe, '--ui-language' ,'en', '--output', output +'.mkv', '--language', '0:eng', '--default-track', '0:yes', '--compression', '0:none', 'decrypted.mp4', '--language', '0:eng', '--default-track', '0:yes', '--compression' ,'0:none', 'decrypted.m4a','--language', '0:eng','--track-order', '0:0,1:0,2:0,3:0,4:0', 'en.srt'])
    print("\nAll Done .....")
else:
    print("Merging .....")
    subprocess.run([mkvmergeexe, '--ui-language' ,'en', '--output', output +'.mkv', '--language', '0:eng', '--default-track', '0:yes', '--compression', '0:none', 'decrypted.mp4', '--language', '0:eng', '--default-track', '0:yes', '--compression' ,'0:none', 'decrypted.m4a','--language', '0:eng','--track-order', '0:0,1:0,2:0,3:0,4:0'])
    print("\nAll Done .....")    

os.remove("encrypted.m4a")
os.remove("encrypted.mp4")
os.remove("decrypted.m4a")
os.remove("decrypted.mp4")
os.remove("keys.txt")
