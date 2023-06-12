# VoiceAssistant
A bodged together offline Voice Assistant based around whisper.

This code is based on [whisper_mic](https://github.com/mallorbc/whisper_mic)  by mallorbc and [whisper](https://github.com/openai/whisper) by openAI, with the exception of evemu, their documentation should cover the dependencies. 
It is probably able to work on most linux distributions however it utilises some search features from GNOME by default. I am using it on Fedora 38 with GNOME on Wayland.

To simulate key presses (which is surprisingly painful to do with wayland) I am using evemu which I learnt about [here](https://fedoramagazine.org/simulate-device-input-evemu/).
When installing on fedora use:
```
sudo dnf install evemu
```
This code probably still won't work immediately due to evemu having to emulate the right device. To fix this change all lines that reference 
```
evemu-event /dev/input/event3
```
with the input event that matches your keyboard when you type 
```
sudo evemu-describe
```
Another thing to note is that I am using a non-standard keyboard shortcut for accessing GNOME search. To make work for you should change the line:
```
sysSearch = "sudo -- bash -c 'evemu-event /dev/input/event9 --type EV_KEY --code KEY_CONNECT --value 1 --sync; evemu-event /dev/input/event9 --type EV_KEY --code KEY_CONNECT --value 0 --sync'"
```
to:
```
sysSearch = "sudo -- bash -c 'evemu-event /dev/input/event(your keyboard event number) --type EV_KEY --code KEY_KEY_(your search shortcut) --value 1 --sync; evemu-event /dev/input/event(your keyboard event number) --type EV_KEY --code KEY_(your search shortcut) --value 0 --sync'"
```

## Some things to note
I am treating this as a project I am invested in more as a distraction from GCSEs so it was never really intended to be a proper solution.
It works entirely offline which is cool and means I don't feel there is a need to implement a wake word.

## Problems
It is clearly a very messy 'solution' but it does kind of work.
Here are some problems I know of so far beyond 'it is messy':
1. The current implementation of the 'search for' command makes it stop working unless a chrome window is already open - fixable by not using chrome or probaby opening a window properly the first time this command is called
2. Some of the keywords I have used are a bit too easy for it to mistake - fixable by changing keywords and using a heavier model
3. Can't handle all characters when it is typing - fixable by sitting down and writing a reference for all characters and their commands
4. Hates sneezes when dictating
5. It is kind of slow to respond once the scentence has finished - I don't know how to fix this but I am sure there is a better way of doing things
6. A bit power hungry to have running constantly on a laptop - I recommend starting it when you want with a macro.
Probably many more that I haven't found noticeable yet.

## License
The model weights of Whisper are released under the MIT License. See their repo for more information.
The whisper_mic is also under the MIT license.
This is availibe under the MIT license.

## Ideas for the future
While I personally don't want to intergrate this with a LLM and TTS it is always cool to do something like that. Intergration with a camera is something I have been considering, this 
could be used to do gestures with hands, feedback from facial expressions or faster end of scentence detection with lip movements - if I did do this I would probably use [mediapipe](https://mediapipe-studio.webapps.google.com/home).
