#!/usr/bin/env python

# System
import sys

# Images
from PIL import Image as PIL_Image
from PIL.ExifTags import TAGS

# Time
import time
import datetime

# Files
from os import listdir
from os.path import isfile, join
import shutil

# Config
import ConfigParser
configFilename = "config.ini"
config = None


######################
# Wrapper for images #
######################
class Image:
    def __init__(self, filename, datetime, model):
        self.filename = filename
        self.datetime = datetime
        self.timestamp = datetime_to_timestamp(datetime)
        self.rawmodel = model
        self.model = model.lower()
    
    def __str__(self):
        return self.filename

    def __repr__(self):
        #return self.filename
        return str( (self.filename, self.datetime, self.model) )

###############################
# Methods using Image wrapper #
###############################

# Create partition of images by camera model
# Returns dictionary from camera model to list of images
def partition(images, sort=True):
    p = {}
    for image in images:
        if image.model not in p:
            p[image.model] = []
        p[image.model].append(image)
    if sort:
        sort_partition(p)
    return p

# Sort each partition by timestamp
def sort_partition(p):
    for model in p:
        sort_by_time(p[model])
    return p

# Use the timestamp to sort by
def sort_by_time(images):
    images.sort(key=lambda x: x.timestamp)
    return images

# Shift every timestamp to fit with a reference
def normalize(images, timestamp, index=0, offset=0): 
    diff = (timestamp - images[index].timestamp) + offset
    return image_shift(images, diff)

# Shift every timestamp by an offset
def image_shift(images, offset=0):
    for image in images:
        image.timestamp += offset
        image.datetime = timestamp_to_datetime(image.timestamp)
    return images

# Use the supplied config options to normalize timestamps
# Config syntax (placed under 'normalize' section):
# <model>: <offset>
def normalize_by_config(p):
    norm_options = config.options("normalize")
    for model in norm_options:
        if model not in p:
            print("No pictures taken with " + model)
        else:
            offset = int(config.get("normalize", model))
            image_shift(p[model], offset)
    return p

# Copy images from the input folder to output folder (defined in config)
# It renames every file to force the order alphabetically
def image_copy(images, input_path, output_path):
    for i, image in zip(range(1, len(images)+1), images):
        shutil.copy(join(input_path, image.filename), join(output_path,  str(i) + "." + ext))


#####################################
# Helper functions or old functions #
#####################################

def image_data(img_input):
    if isinstance(img_input, str):
        try:
            img = PIL_Image.open(img_input)
        except IOError:
            img = None
            print "'" + img_input + "' not found or not image"
    else:
        img = img_input

    if img is None:
        return (None, None)

    exif = img._getexif()

    datetime = exif[36867]
    model = exif[272]
    make = exif[271].split(" ", 1)[0] # Take first word of make
    if not model.startswith(make):
        model = make + " " + model
    return (datetime, model)

def image_all_data(filename):
    img = Image.open(filename)
    exif = {
        TAGS[k]: v
        for k, v in img._getexif().items()
        if k in TAGS
    }
    return exif

def tagcode(*tags):
    d = {} 
    for key in TAGS:
        if TAGS[key] in tags:
            d[TAGS[key]] = key
    if len(tags) == 1:
        return d[tags[0]] 
    else:
        return d

def datetime_to_timestamp(s):
    return int(time.mktime(datetime.datetime.strptime(s, "%Y:%m:%d %H:%M:%S").timetuple()))

def timestamp_to_datetime(t):
    return datetime.datetime.fromtimestamp(int(t)).strftime("%Y:%m:%d %H:%M:%S")

def image_time_taken(image_file):
    data = image_data(image_file)
    if data == (None, None):
        return None
    else:
        t = data[0]
        return datetime_to_timestamp(t)

def image_sort_time_old(images, path="."):
    images.sort(key=lambda x: image_time_taken(join(path, x)))
    return images

def image_partition_old(images, path="."):
    p = {}
    for image in images:
        model = image_data(join(path, image))[1]
        if model is None:
            continue
        if model not in p:
            p[model] = []
        p[model].append(image)
    return p


def load_files_in_folder(path):
    return [ f for f in listdir(path) if isfile(join(path,f)) ]

def create_image_wrappers(files):
    images = []
    for f in files:
        data = image_data(join(input_path, f))
        if data == (None, None): 
            continue
        img = Image(f, data[0], data[1])
        images.append(img)
    return images


#############
# Bootstrap #
#############
if __name__ == '__main__':
    # Read command line arguments
    print_models = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "models":
            print_models = True

    # Parse config file
    config = ConfigParser.ConfigParser()
    config.read(configFilename)
    
    input_path = config.get("main", "input_path")
    output_path = config.get("main", "output_path")
    ext = config.get("main", "extension")

    # Load and process images
    files = load_files_in_folder(input_path)
    images = create_image_wrappers(files)

    # Create partition by camera model
    p = partition(images)

    # If 'models' was passed, print the models
    if print_models:
        for model in p:
            print model
    else: # Do your actual thing
        if config.has_section("normalize"):
            normalize_by_config(p)
    
        sort_by_time(images)

        image_copy(images, input_path, output_path)

