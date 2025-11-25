import datetime
import time


def sleep(duration):
    return time.sleep(duration)

def formatdate(date=None):
    date = datetime.datetime.now() if date is None else date
    return date.strftime("%d/%m/%Y %H:%M")

def formatdate_HM(date=None):
    date = datetime.datetime.now() if date is None else date
    return date.strftime("%H:%M")

def time_interval(key):
    if "w" in key and "d" in key and "h" in key and "m" in key and "s" in key:
        key.replace("w", " ").replace("d", " ").replace("h", " ").replace("m", " ").replace("s", " ")
        tag = "w/d/h/m/s"
    elif "w" in key and "h" in key and "m" in key and "s" in key:
        key.replace("w", " ").replace("h", " ").replace("m", " ").replace("s", "")
        tag = "w/h/m/s"
    elif "w" in key and "m" in key and "s" in key:
        key.replace("w", " ").replace("m", " ").replace("s", " ")
        tag = "w/m/s"
    elif "w" in key and "s" in key:
        key.replace("w", " ").replace("s", " ")
        tag = "w/s"
    elif "d" in key and "h" in key and "m" in key and "s" in key:
        key.replace("d", " ").replace("h", " ").replace("m", " ").replace("s", " ")
        tag = "d/h/m/s"
    elif "d" in key and "m" in key and "s" in key:
        key.replace("d", " ").replace("m", " ").replace("s", " ")
        tag = "d/m/s"
    elif "d" in key and "s" in key:
        key.replace("d", " ").replace("s", " ")
        tag = "d/s"
    elif "h" in key and "m" in key and "s" in key:
        key.replace("h", " ").replace("m", " ").replace("s", " ")
        tag = "h/m/s"
    elif "h" in key and "m" in key:
        key.replace("h", " ").replace("m", " ")
        tag = "h/m"
    elif "m" in key and "s" in key:
        key.replace("m", " ").replace("s", " ")
        tag = "m/s"
    elif "h" in key and "s" in key:
        key.replace("h", " ").replace("s", " ")
        tag = "h/s"
    elif "w" in key:
        key.replace("w", " ")
        tag = "w"
    elif "d" in key:
        key.replace("d", " ")
        tag = "d"
    elif "h" in key:
        key.replace("h", " ")
        tag = "h"
    elif "m" in key:
        key.replace("m", " ")
        tag = "m"
    elif "s" in key:
        key.replace("s", " ")
        tag = "s"

    tags=tag
    
    time_list = key.split()
    time_list.append(tags)
    return time_list
