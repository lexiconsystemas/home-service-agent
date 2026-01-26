"""Worker entry point."""

from app.workers.queue import start_worker

if __name__ == "__main__":
    start_worker()
