import subprocess

def convert(mkv_file):
    command = "ffmpeg -i {0} -ab 160k -ac 2 -ar 44100 -vn audio.wav".format(mkv_file)

    subprocess.call(command, shell=True)

