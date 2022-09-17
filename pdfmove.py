from os import PathLike
import os
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog import events
from pathlib import Path


def move_pdf(src_file: PathLike, dest_dir: PathLike):
    try:
        src_path = Path(src_file)
        dest_path = Path(dest_dir)
        if not src_path.exists():
            return
        reader = PdfReader(src_path)
        info = reader.getDocumentInfo()
        title = info.title
        # author = info.author
        # date = info['/CreationDate']
        name = src_path.name if title is None or title == "" else title + '.pdf'
        src_path.rename(dest_path / name)
    except PdfReadError:
        pass


class RenameAndMovePDF(LoggingEventHandler):
    def __init__(self, target_dir: PathLike):
        super().__init__()
        self.target_dir = target_dir

    def on_moved(self, event: events.FileSystemEvent):
        super().on_moved(event)
        if isinstance(event, events.FileMovedEvent):
            move_pdf(event.dest_path, self.target_dir)

    def on_created(self, event: events.FileSystemEvent):
        super().on_created(event)
        if isinstance(event, events.FileCreatedEvent):
            move_pdf(event.src_path, self.target_dir)

    def on_deleted(self, event: events.FileSystemEvent):
        super().on_deleted(event)

    def on_modified(self, event: events.FileSystemEvent):
        super().on_modified(event)
        if isinstance(event, events.FileModifiedEvent):
            move_pdf(event.src_path, self.target_dir)


src = os.getenv('SRC')
target = os.getenv('TARGET')
assert src is not None and target is not None

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

event_handler = RenameAndMovePDF(target)
observer = Observer()
observer.schedule(event_handler, src, recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
