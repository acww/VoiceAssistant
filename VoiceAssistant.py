"""A bodged together implementation of an offline voice assissitant
using whisper from openAI (https://github.com/openai/whisper) 
and based of this repository 
https://github.com/mallorbc/whisper_mic
"""

import whisper
import speech_recognition as sr
import os
import time
import queue
import threading
import torch
import numpy as np

# The command used to trigger the gnome search shortcut
sysSearch = "sudo -- bash -c 'evemu-event /dev/input/event9 --type EV_KEY --code KEY_CONNECT --value 1 --sync; evemu-event /dev/input/event9 --type EV_KEY --code KEY_CONNECT --value 0 --sync'"
# Command to press enter
enter = "sudo -- bash -c 'evemu-event /dev/input/event3 --type EV_KEY --code KEY_ENTER --value 1 --sync; evemu-event /dev/input/event3 --type EV_KEY --code KEY_ENTER --value 0 --sync'"

# In each tuple there are two lists. The first list contains keywords and the second list contains actions. 
# Actions should appear in the list in order of execution and commands with a single keyword should appear after commands with that keyword and more
commands = [(['open', 'base', 'firmware'], ['code -n', "code -a /home/$USER/Projects/Checkpoints/firmwareBase", "code -g /home/$USER/Projects/Checkpoints/firmwareBase/src/modules/NFCModule.cpp"]),    # In a new VSC window open a directory and then open the file NFCModule.cpp
            (['open', 'checkpoint', 'firmware'], ['code -n', "code -a /home/%USER/Projects/Checkpoints/firmwareCheckpoint", "code -g /home/$USER/Projects/Checkpoints/firmwareCheckpoint/src/modules/NFCModule.cpp"]),
            (['open', 'my', 'experiment'], ['code -n', "code -g /home/$USER/Projects/VoiceAssistant.py"]),  #In a new VSC window open this project
            (['open'], [sysSearch, 'write', enter]),  # Using gnome search open the spoken app
            (['search', 'for'],['google-chrome-stable --new-window', 'write', enter]),  # Search for something in a new window in google chrome
            (['start', 'transcribe'], ['startTranscribe']), # Start transcribe
            (['stop', 'transcribe'], ['stopTranscribe']),   # Stope transcribe
            (['enter', 'text'], ['write']), # Type text (keywords are quite unreliable)
            (['kill', 'whisper'], ['pkill python']),    # kill this program
            (['return'], [enter])]  # press enter (keyword is quite unreliable)


def getKeyPressCommand(name):   # Generate a command to press given key (only works if you pass the correct name)
    name = "KEY_"+name
    return "sudo -- bash -c 'evemu-event /dev/input/event3 --type EV_KEY --code "+name+" --value 1 --sync; evemu-event /dev/input/event3 --type EV_KEY --code "+name+" --value 0 --sync'"

def pressKey(key, runCommand = True):   
    # This is the code I have used to enter text/keystrokes. 
    # If you are using something other than wayland as your windowing system there is propbably a nicer option like pyautogui
    # It took me a long time to find anything that worked but eventually this gave me a working solution
    # https://fedoramagazine.org/simulate-device-input-evemu/ 
    if key == "enter":
        command = getKeyPressCommand(key.upper())
    elif 64 < ord(key) < 91 or 96 < ord(key) < 123 or 47<ord(key)<58: # Character and number keys
        if 64 < ord(key) < 91: # If its a capital letter we press shift down
            os.system("sudo -- bash -c 'evemu-event /dev/input/event3 --type EV_KEY --code KEY_LEFTSHIFT --value 1 --sync'")
        command = getKeyPressCommand(key.upper())
    elif key == " ":    # If it is space we need to pass it the keys name instead
        command = getKeyPressCommand("SPACE")
    else:               # Any unknown characters we just ignore
        runCommand = False
    if runCommand:
        os.system(command)  # run the key press
        os.system("sudo -- bash -c 'evemu-event /dev/input/event3 --type EV_KEY --code KEY_LEFTSHIFT --value 0 --sync'") # Release shift



"""I am using tiny model as I've found it to be more than adequate most of the time and it's supposedly fastest.
Using just the english model means i can massively reduce the quantity of misinterpretations.
I might in the future use the probability from enabling verbose to decide whether a command is worth executing (based on the probability 
and whether the command has been done before)
Energy and pause are used to segment the audio check out the speech_recognition library documetation for more infomation.
Since I have a graphics card with cuda support I'm using it."""
def main(model='tiny.en', english=True, verbose=False, energy=300, pause=0.8, device='cuda'):

    audio_model = whisper.load_model(model).to(device)

    audio_queue = queue.Queue()
    result_queue = queue.Queue()
    threading.Thread(target=record_audio,
                     args=(audio_queue, energy, pause)).start() # Audio recording and segmentation
    threading.Thread(target=transcribe_forever,
                     args=(audio_queue, result_queue, audio_model, english, verbose)).start()   # Audio recognition

    transcribe = False

    while True:
        writeText = result_queue.get()   # Wait for text to be given
        print(writeText)
        text = writeText.lower()    # The text that we write wants capitals but its easier to search text for keywords without that

        for command in commands: # Check every set of keywords
            
            keywords = command[0]
            actions = command[1]

            success = 0
            for keyword in keywords:        # Check for keywords in the text we've been given
                if text.find(keyword) != -1:
                    success += 1
            
            if success == len(keywords):   # If all the keywords for a command were found we run the actions associated with that command

                for action in actions:

                    if action == 'stopTranscribe':  # stop transcribing (this needs to be done even when we are transcribing which is why we still enter this loop)
                        print('stopping transcribe')
                        transcribe = False
                        break

                    if not transcribe:  # when we are transcribing we dont want to do actions

                        if action == 'startTranscribe': # start transcribing
                            transcribe = True
                            print('Starting transcribe')
                            break

                        if action == 'enter':   # press enter
                            pressKey('enter')
                        
                        elif action == 'write': # type text
                            writeText = writeText[text.index(keywords[-1])+len(keywords[-1]):len(text)+1]   # The text we want to type appears immediatly after the last keyword 
                            for char in writeText:
                                pressKey(char)
                        
                        else:   # If it isn't a special action then it is a action for the command line
                            os.system(action)
                            time.sleep(0.1)     # A delay is used so that if we are opening a window we dont disrupt that process with the next command
                if not transcribe:
                    break
        
        if transcribe:              # When we are transcribing we type text no matter what keywords were said (except fot the stop transcripe command)
            for char in writeText:
                pressKey(char)



def record_audio(audio_queue, energy, pause):   # record and stop recording the audio continuously
    #load the speech recognizer and set the initial energy threshold and pause threshold
    r = sr.Recognizer()
    r.energy_threshold = energy
    r.pause_threshold = pause
    r.dynamic_energy_threshold = False # I've found it works better without this

    with sr.Microphone(sample_rate=16000) as source:    
        print("Say something!")
        i = 0
        while True:
            #get and save audio to wav file
            audio = r.listen(source)
            torch_audio = torch.from_numpy(np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0)
            audio_data = torch_audio

            audio_queue.put_nowait(audio_data)
            i += 1


def transcribe_forever(audio_queue, result_queue, audio_model, english, verbose):   # Generate text from the provided audio
    while True:
        audio_data = audio_queue.get()
        if english:
            result = audio_model.transcribe(audio_data,language='english')
        else:
            result = audio_model.transcribe(audio_data)

        if not verbose:
            predicted_text = result["text"]
            result_queue.put_nowait(predicted_text)
        else:
            result_queue.put_nowait(result)

main()  # Run the code