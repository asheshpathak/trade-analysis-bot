"""
Concurrency utilities for parallel processing in stock analysis.
"""
import asyncio
import concurrent.futures
import functools
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from config.settings import MAX_THREADS, MAX_WORKERS


class ThreadPool:
    """
    Thread pool for parallel processing.

    Features:
    - Execute tasks in parallel using threads
    - Manage thread lifecycle
    - Collect results from multiple threads
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize thread pool.

        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers or MAX_THREADS
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        logger.info(f"Thread pool initialized with {self.max_workers} workers")

    def map(self, func: Callable, items: List[Any]) -> List[Any]:
        """
        Apply a function to each item in parallel.

        Args:
            func: Function to apply
            items: List of items to process

        Returns:
            List of results
        """
        try:
            logger.info(f"Starting parallel processing of {len(items)} items")
            results = list(self.executor.map(func, items))
            logger.info(f"Completed parallel processing of {len(items)} items")
            return results
        except Exception as e:
            logger.error(f"Error in parallel processing: {str(e)}")
            return []

    def execute(self, tasks: List[Tuple[Callable, List[Any], Dict[str, Any]]]) -> List[Any]:
        """
        Execute multiple tasks in parallel.

        Args:
            tasks: List of tuples (function, args, kwargs)

        Returns:
            List of results
        """
        try:
            futures = []

            for func, args, kwargs in tasks:
                future = self.executor.submit(func, *args, **kwargs)
                futures.append(future)

            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            return results
        except Exception as e:
            logger.error(f"Error executing parallel tasks: {str(e)}")
            return []

    def shutdown(self):
        """Shut down the thread pool."""
        self.executor.shutdown()
        logger.info("Thread pool shut down")


class ProcessPool:
    """
    Process pool for CPU-intensive parallel processing.

    Features:
    - Execute tasks in parallel using processes
    - Manage process lifecycle
    - Collect results from multiple processes
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize process pool.

        Args:
            max_workers: Maximum number of worker processes
        """
        self.max_workers = max_workers or MAX_WORKERS
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)
        logger.info(f"Process pool initialized with {self.max_workers} workers")

    def map(self, func: Callable, items: List[Any]) -> List[Any]:
        """
        Apply a function to each item in parallel.

        Args:
            func: Function to apply
            items: List of items to process

        Returns:
            List of results
        """
        try:
            logger.info(f"Starting parallel processing of {len(items)} items")
            results = list(self.executor.map(func, items))
            logger.info(f"Completed parallel processing of {len(items)} items")
            return results
        except Exception as e:
            logger.error(f"Error in parallel processing: {str(e)}")
            return []

    def execute(self, tasks: List[Tuple[Callable, List[Any], Dict[str, Any]]]) -> List[Any]:
        """
        Execute multiple tasks in parallel.

        Args:
            tasks: List of tuples (function, args, kwargs)

        Returns:
            List of results
        """
        try:
            futures = []

            for func, args, kwargs in tasks:
                future = self.executor.submit(func, *args, **kwargs)
                futures.append(future)

            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            return results
        except Exception as e:
            logger.error(f"Error executing parallel tasks: {str(e)}")
            return []

    def shutdown(self):
        """Shut down the process pool."""
        self.executor.shutdown()
        logger.info("Process pool shut down")


class PeriodicTask:
    """
    Execute a task periodically in a separate thread.

    Features:
    - Run task at specified intervals
    - Start, stop, and pause execution
    - Adjust interval dynamically
    """

    def __init__(self, func: Callable, interval: int, *args, **kwargs):
        """
        Initialize periodic task.

        Args:
            func: Function to execute
            interval: Execution interval in seconds
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
        """
        self.func = func
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self.running = False
        self.paused = False
        self.thread = None
        self._stop_event = threading.Event()

        logger.info(f"Periodic task initialized with interval {interval}s")

    def _run(self):
        """Run the task periodically."""
        while not self._stop_event.is_set():
            if not self.paused:
                try:
                    start_time = time.time()
                    self.func(*self.args, **self.kwargs)
                    execution_time = time.time() - start_time

                    # Adjust sleep time to maintain consistent interval
                    sleep_time = max(0.1, self.interval - execution_time)

                    logger.debug(f"Task executed in {execution_time:.2f}s, sleeping for {sleep_time:.2f}s")
                except Exception as e:
                    logger.error(f"Error in periodic task: {str(e)}")

            # Check stop event every 0.1 seconds to allow for clean shutdown
            for _ in range(int(self.interval * 10)):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)

    def start(self):
        """Start the periodic task."""
        if not self.running:
            self.running = True
            self.paused = False
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Periodic task started")

    def stop(self):
        """Stop the periodic task."""
        if self.running:
            self._stop_event.set()
            if self.thread:
                self.thread.join(timeout=self.interval + 1)
            self.running = False
            logger.info("Periodic task stopped")

    def pause(self):
        """Pause the periodic task."""
        self.paused = True
        logger.info("Periodic task paused")

    def resume(self):
        """Resume the paused periodic task."""
        self.paused = False
        logger.info("Periodic task resumed")

    def set_interval(self, interval: int):
        """
        Update the execution interval.

        Args:
            interval: New interval in seconds
        """
        self.interval = interval
        logger.info(f"Periodic task interval updated to {interval}s")


def async_to_sync(func):
    """
    Decorator to convert async function to sync function.

    Args:
        func: Async function to convert

    Returns:
        Synchronous wrapper function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))

    return wrapper


def run_in_thread(func):
    """
    Decorator to run function in a separate thread.

    Args:
        func: Function to run in thread

    Returns:
        Thread wrapper function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper