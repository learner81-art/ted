#!/usr/bin/env python3
import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from gitignore_parser import parse_gitignore

class GitAutoCommitHandler(FileSystemEventHandler):
    def __init__(self, gitignore):
        self.gitignore = gitignore
        self.last_commit_time = 0
        self.debounce_seconds = 2  # 防抖时间
        self.watch_patterns = ["*.py", "*.html", "*.js"]
        self.ignore_patterns = ["*.log"]

    def should_handle(self, path):
        # 检查文件类型是否在监控范围内
        if not any(path.endswith(p.replace("*", "")) for p in self.watch_patterns):
            return False
            
        # 检查是否在.gitignore中
        if self.gitignore and self.gitignore(path):
            return False
            
        # 检查是否在额外忽略模式中
        if any(path.endswith(p.replace("*", "")) for p in self.ignore_patterns):
            return False
            
        return True

    def on_modified(self, event):
        if not event.is_directory and self.should_handle(event.src_path):
            current_time = time.time()
            if current_time - self.last_commit_time > self.debounce_seconds:
                self.last_commit_time = current_time
                self.commit_changes()

    def commit_changes(self):
        try:
            subprocess.run(["git", "add", "-u"], check=True)
            subprocess.run(["git", "commit", "-m", f"Auto commit: {time.strftime('%Y-%m-%d %H:%M:%S')}"], check=True)
            print(f"Auto committed at {time.strftime('%H:%M:%S')}")
        except subprocess.CalledProcessError as e:
            print(f"Commit failed: {e}")

def main():
    gitignore_path = os.path.join(os.getcwd(), ".gitignore")
    gitignore = parse_gitignore(gitignore_path) if os.path.exists(gitignore_path) else None
    
    event_handler = GitAutoCommitHandler(gitignore)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
