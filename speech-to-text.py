#!/usr/bin/env python3

import speech_recognition as sr
# obtain path to "english.wav" in the same folder as this script
from os import path
from convert_mkv_wav import convert
from pyChatGPT import ChatGPT
import logging
# ChatGTP Session token
logging.basicConfig(level=logging.DEBUG)
session_tocken = '<YOUR SESSION TOKEN>'

# convert to wav format
convert('audio.mkv')

AUDIO_FILE = path.join(path.dirname(path.realpath(__file__)), "audio.wav")

# use the audio file as the audio source
r = sr.Recognizer()
with sr.AudioFile(AUDIO_FILE) as source:
    audio = r.record(source)  # read the entire audio file

# Using a microphone
# with sr.Microphone() as source:
#   #Chama a funcao de reducao de ruido disponivel na speech_recognition
#   r.adjust_for_ambient_noise(source)
#   #Avisa ao usuario que esta pronto para ouvir
#   print("Speak: ")
#   #Armazena a informacao de audio na variavel
#   audio = r.listen(source)

# recognize speech using Google Speech Recognition
try:
    # for testing purposes, we're just using the default API key
    # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
    # instead of `r.recognize_google(audio)`
    msg  = r.recognize_google(audio, language='pt-BR')
    print("Transcript> " + msg)    
    # Here you can set your conversation id - OR just remove it
    api = ChatGPT(session_token, conversation_id='9f02d513-c6de-4cfa-898b-cd6fba91dbd9')
    enhanced_text = api.send_message('Corrija esse trecho: '+msg)
    print("ChatGPT> " + enhanced_text['message'])
    output = open('enhanced-text.txt', 'w')
    output.write(enhanced_text['message'])
    output.close()
except sr.UnknownValueError:
    print("Google Speech Recognition could not understand audio")
except sr.RequestError as e:
    print("Could not request results from Google Speech Recognition service; {0}".format(e))

