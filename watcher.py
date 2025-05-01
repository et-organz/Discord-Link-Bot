import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from subprocess import Popen

class Watcher:
    def __init__(self, bot_script):
        self.bot_script = bot_script
        self.observer = Observer()
        self.handler = FileSystemEventHandler()
        self.handler.on_modified = self.on_modified

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f'File modified: {event.src_path}')
            self.restart_bot()

    def start(self):
        self.observer.schedule(self.handler, '.', recursive=True)
        self.observer.start()

    def restart_bot(self):
        print('Restarting bot...')
        os.system('pkill -f python')  # Stop the running bot process
        time.sleep(1)  # Wait for the process to terminate
        Popen([sys.executable, self.bot_script])  # Start the bot again

if __name__ == '__main__':
    bot_script = 'main.py'  # Replace with your bot's entry script
    watcher = Watcher(bot_script)
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.observer.stop()
        print('Watcher stopped.')
    watcher.observer.join()
