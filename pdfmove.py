# TODO: extend to a command line based system (e.g.,
# sync renaming between raw papers and notes)

from os import PathLike
import os
import threading
from typing import Dict, Iterable, List
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog import events
from pathlib import Path
import shutil


def move_pdf(src_file: PathLike, dest_dirs: Iterable[PathLike]):
    dest_dirs_iter = iter(dest_dirs)
    first_dir = next(dest_dirs_iter)
    try:
        src_path = Path(src_file)
        dest_paths = (Path(dest_dir) for dest_dir in dest_dirs_iter)
        if not src_path.exists():
            return
        reader = PdfReader(src_path)
        info = reader.getDocumentInfo()
        title = info.title
        # author = info.author
        # date = info['/CreationDate']
        name = src_path.name if title is None or title == "" else title + '.pdf'
        for dest_path in dest_paths:
            shutil.copy2(src_path, dest_path / name)
        src_path.rename(first_dir / name)
    except PdfReadError:
        pass


class RenameAndMovePDF(LoggingEventHandler):
    def __init__(self, target_dir: List[PathLike]):
        super().__init__()
        self.target_dir = target_dir
        self.lock: Dict[Path, threading.Lock] = {}

    def acquire(self, id: Path):
        if id not in self.lock:
            self.lock[id] = threading.Lock()
        self.lock[id].acquire(blocking=True)

    def release(self, id: Path):
        self.lock[id].release()

    def on_moved(self, event: events.FileSystemEvent):
        super().on_moved(event)
        if isinstance(event, events.FileMovedEvent):
            self.acquire(event.dest_path)
            move_pdf(event.dest_path, self.target_dir)
            self.release(event.dest_path)

    def on_created(self, event: events.FileSystemEvent):
        super().on_created(event)
        if isinstance(event, events.FileCreatedEvent):
            self.acquire(event.src_path)
            move_pdf(event.src_path, self.target_dir)
            self.release(event.src_path)

    def on_deleted(self, event: events.FileSystemEvent):
        super().on_deleted(event)

    def on_modified(self, event: events.FileSystemEvent):
        super().on_modified(event)
        if isinstance(event, events.FileModifiedEvent):
            self.acquire(event.src_path)
            move_pdf(event.src_path, self.target_dir)
            self.release(event.src_path)


src = os.getenv('SRC')
targets = os.getenv('TARGET')
assert src is not None
assert targets is not None
assert targets != ""

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

event_handler = RenameAndMovePDF(list(map(Path, targets.split(os.pathsep))))
observer = Observer()
observer.schedule(event_handler, src, recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
