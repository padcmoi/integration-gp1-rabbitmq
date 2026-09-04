"""Start the consumer inside the application that hosts it.

`main.py` is a process someone has to launch and keep alive. When the bus lives
inside GP1, nobody launches it: restarting the application restarts Django and
nothing else, so the mailbox is never declared and never read, and the whole bus
looks silently dead.

This is the other way in. One line where the application boots:

    from rabbit_bus.boot import start_in_background

    start_in_background()

and the consumer runs in a daemon thread of that process: it declares its inbox
at every connection, consumes it, and dies with the application. `AmqpPublish`
stays what it is, the publisher side, and never declares anything.

Called twice, it starts once: Django's autoreloader imports the app twice in
development, and two consumers in one process would take turns eating the same
messages."""

import logging
import sys
import threading
from pathlib import Path

logger = logging.getLogger("bus.boot")

BASE_DIR = Path(__file__).resolve().parent

_lock = threading.Lock()
_thread = None


def start_in_background(daemon=True):
    """Run the bus consumer in a thread of the calling process.

    Answers the thread, already running, or the one started earlier. Never
    raises: an application must not fail to boot because a broker is down, and
    the consumer reconnects on its own anyway."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            logger.info("consumer already running in this process")
            return _thread
        try:
            # main.py speaks of `consumers` and `publishers` as top-level
            # packages, the way it sees them when run from this directory. The
            # hosting application knows nothing of that, so we say it here.
            if str(BASE_DIR) not in sys.path:
                sys.path.insert(0, str(BASE_DIR))
            from .main import Bus, load_env, setup_logging

            setup_logging()
            bus = Bus(load_env())
            _thread = threading.Thread(target=bus.run_forever, name="rabbit-bus", daemon=daemon)
            _thread.start()
            logger.info("consumer started in background on %s", bus.queue_name)
            return _thread
        except Exception as error:
            logger.warning("consumer could not start (%s: %s)", type(error).__name__, error)
            return None
