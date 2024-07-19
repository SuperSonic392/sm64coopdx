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
    file_list = files if files[0] != "*" else os.listdir(path)
    for file in file_list:
        file_path = os.path.join(SAMPLE_PATH, file)
        if not os.path.exists(file_path):
            shutil.copyfile(os.path.join(path, file), file_path)