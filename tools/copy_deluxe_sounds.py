import os
import shutil

SAMPLE_PATH = "sound/samples/deluxe"

instrument_targets = {
    "sound/samples/bowser_organ": [ "00_organ_1.aiff", "01_organ_1_lq.aiff" ],
    "sound/samples/course_start": [ "*" ],
    "sound/samples/piranha_music_box": [ "*" ],
    "sound/samples/instruments": [ "*" ],
    "sound/samples/sfx_9": [ "00.aiff", "01.aiff", "02.aiff" ],
}

if not os.path.exists(SAMPLE_PATH):
    os.makedirs(SAMPLE_PATH)

for path, files in instrument_targets.items():
    fileList = files if files[0] != "*" else os.listdir(path)
    for file in fileList:
        shutil.copyfile(os.path.join(path, file), os.path.join(SAMPLE_PATH, file))