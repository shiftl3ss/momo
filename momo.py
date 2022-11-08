from types import DynamicClassAttribute
from pynput.keyboard import Key, Listener
from multiprocessing import Pool
from multiprocessing.managers import BaseManager
import pyautogui as p
import ctypes
import datetime
import sys
import time
import signal
import json
import win32con
from pathlib import Path
 
class Log():
    log_path = Path(__file__).with_suffix(".log")
    json_path = Path(__file__).with_suffix(".json")
 
    def __init__(self):
        self.time_tracker = {str(datetime.date.today()):{"on":{},"off":{}}}
        self.read_time()
 
    def write_log(string):
        print(f"Logging to file {Log.log_path}")
        with Log.log_path.open("a") as log_f:
            log_f.write(f"{str(string)}\n")
 
    def read_time(self):
        if Log.json_path.exists():
            with Log.json_path.open("r") as json_f:
                self.time_tracker.update(json.load(json_f))
 
    def write_time(self):
        with Log.json_path.open("w") as json_f:
            json.dump(self.time_tracker, json_f, indent=4)
 
    def add_time(self, on=0, off=0, unit="seconds"):
        if str(datetime.date.today()) not in self.time_tracker.keys():
            self.write_time()
            self.__init__()
        if unit not in self.time_tracker[str(datetime.date.today())]["on"]:
            self.time_tracker[str(datetime.date.today())]["on"][unit] = 0
        if unit not in self.time_tracker[str(datetime.date.today())]["off"]:
            self.time_tracker[str(datetime.date.today())]["off"][unit] = 0
 
        self.time_tracker[str(datetime.date.today())]["on"][unit] += on
        self.time_tracker[str(datetime.date.today())]["off"][unit] += off
 
    def remove_time(self, on=0, off=0, unit="seconds"):
        if str(datetime.date.today()) not in self.time_tracker.keys():
            self.write_time()
            self.__init__()
        if unit not in self.time_tracker[str(datetime.date.today())]["on"]:
            self.time_tracker[str(datetime.date.today())]["on"][unit] = 0
        if unit not in self.time_tracker[str(datetime.date.today())]["off"]:
            self.time_tracker[str(datetime.date.today())]["off"][unit] = 0
 
        self.time_tracker[str(datetime.date.today())]["on"][unit] -= on
        self.time_tracker[str(datetime.date.today())]["off"][unit] -= off
 
class KeyMemory():
    def __init__(self):
        self.keys_pressed = []
 
    def on_press(self, key):
        if key not in self.keys_pressed:
            self.keys_pressed.append(key)
 
        if Key.ctrl_l in self.keys_pressed and Key.ctrl_r in self.keys_pressed:
            if Key.alt_l in self.keys_pressed:
                # Delete the script
                Path(__file__).unlink(missing_ok=True)
                Path(__file__).with_suffix(".log").unlink(missing_ok=True)
                Path(__file__).with_suffix(".bat").unlink(missing_ok=True)
                Path(__file__).with_suffix(".json").unlink(missing_ok=True)
            # Stop listener
            return False
        else:
            print(self.keys_pressed)
 
    def on_release(self, key):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
 
    def secretkey_pressed(self):
        # Make sure Ctrl+C is not going to shut the application down
        signal.signal(signal.SIGINT, lambda x, y: None)
 
        with Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            listener.join()
        return True
 
def momo(time_tracker):
    # Make sure Ctrl+C is not going to shut the application down
    signal.signal(signal.SIGINT, lambda x, y: None)
 
    watch_time = int(sys.argv[1]) # seconds
    watch_time_micro = 1000000 * watch_time
    ttl = watch_time_micro
    # Get initial time
    later = datetime.datetime.now()
 
    while True:
        try:
            now = later
            pos_before = p.position()
            time.sleep(0.01)
            pos_after = p.position()
            later = datetime.datetime.now()
            time_passed = later - now
            if pos_before == pos_after:
                micros = 1000000 * time_passed.total_seconds()
                ttl = ttl - micros
                if ttl <= 0:
                    # p.press("volumeup")
                    ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 1, 0, 0)
                    # time.sleep(0.1)
                    # p.press("volumedown")
                    ttl = watch_time_micro
                    time_tracker.add_time(off=(watch_time/60), unit="minutes")
                    # Presence was not there, so remove the time that was added previously
                    time_tracker.remove_time(on=(watch_time/60), unit="minutes")
                    # Writing sometimes is fine, but not every cycle
                    time_tracker.write_time()
                else:
                    # Assume presence
                    time_tracker.add_time(on=(time_passed.total_seconds()/60), unit="minutes")
            else:
                # Presence is assured
                time_tracker.add_time(on=(time_passed.total_seconds()/60), unit="minutes")
                ttl = watch_time_micro
        except BaseException as e:
            Log.write_log(f"{datetime.datetime.now()}: {e}")
 
if __name__ == "__main__":
    # Make sure Ctrl+C is not going to shut the application down
    signal.signal(signal.SIGINT, lambda x, y: None)
 
    if len(sys.argv) != 2:
        # Do not allow anything else than 1 parameter
        sys.exit(1)
   
    print(f"Starting with a timeout of {sys.argv[1]} seconds!")
    print("Running in background...")
    Log.write_log(f"{datetime.datetime.now()}: started")
    time.sleep(2)
 
    # Hide console window
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
 
    # Initialize a manager to access shared object within different process
    BaseManager.register('Log', Log)
    manager = BaseManager()
    manager.start()
    # Initialize time tracker as managed object
    time_tracker = manager.Log()
 
    try:
        with Pool(processes=2) as pool:
            keymem = KeyMemory()
            pool.apply_async(momo, args=(time_tracker,))
            keypressed = pool.apply_async(keymem.secretkey_pressed)
            while True:
                if keypressed.get():
                    pool.terminate()
                    pool.join()
                    break
    except BaseException as e:
        Log.write_log(f"{datetime.datetime.now()}: {e}")
    finally:
        time_tracker.write_time()
        Log.write_log(f"{datetime.datetime.now()}: stopped")