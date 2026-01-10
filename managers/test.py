"""
Diagnostic script for CommandsManager

Purpose
- Run a self-contained diagnostic that exercises CommandsManager handlers and
  writes detailed debug logs to logs/commands_diagnostic.log.
- Help you find why a "hello" command appears to "take too long" or is not handled
  correctly by logging:
    - queue enqueue/dequeue events
    - handler start / end / elapsed time
    - timeout events and cancellations
    - exceptions and stack traces
    - active handler introspection

Usage
- Place this file in your project (e.g., project_root/tools/diagnose_commands.py).
- From the project root run:
    python -m tools.diagnose_commands
  or
    python tools/diagnose_commands.py

Notes
- The script will try to import your CommandsManager from a few common locations.
  Edit the IMPORT_PATHS list below if your CommandsManager lives elsewhere.
- It creates a CommandsManager instance with a short handler_timeout so timeouts are easy to reproduce.
- It registers two hello-like handlers (fast and slow) and submits commands to provoke both normal completion and timeout/cancellation behavior.
- Open logs/commands_diagnostic.log after running to inspect the full diagnostic trace.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict

# Try importing CommandsManager from likely module paths; edit if needed.
IMPORT_PATHS = [
    "ui.commands.commands_manager",   # recommended location used in examples
    "ui.commands_manager",
    "commands_manager",
    "ui.commands.commands_manager.commands_manager",
]

CommandsManager = None
CommandRequest = None
CommandResponse = None

for path in IMPORT_PATHS:
    try:
        module = __import__(path, fromlist=["*"])
        # module may expose CommandsManager at top-level
        if hasattr(module, "CommandsManager"):
            CommandsManager = getattr(module, "CommandsManager")
        # fallback: check for other names
        if CommandsManager is None:
            for attr in ("commands_manager", "CommandsManager"):
                if hasattr(module, attr):
                    CommandsManager = getattr(module, attr)
        # get dataclasses if available
        CommandRequest = getattr(module, "CommandRequest", None)
        CommandResponse = getattr(module, "CommandResponse", None)
        if CommandsManager:
            break
    except Exception:
        continue

if CommandsManager is None:
    print("ERROR: Could not import CommandsManager from any of the known paths.")
    print("Please adjust IMPORT_PATHS in this script to point to your CommandsManager module.")
    sys.exit(1)

# Setup logging directory and file
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_DIR = os.path.abspath(LOG_DIR)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "commands_diagnostic.log")

# Configure a logger dedicated for diagnostics
logger = logging.getLogger("commands_diagnostic")
logger.setLevel(logging.DEBUG)
# rotate if large (keeps simple single file here)
handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s", "%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Also log to stdout for immediate feedback
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


async def run_diagnostics():
    """
    Create CommandsManager, register handlers, submit commands, and log diagnostics.
    """
    logger.info("Starting diagnostics run")

    # Create CommandsManager with short timeout to force observable timeouts
    cm = CommandsManager(core=None, handler_timeout=3.0, compatibility_mode=False, logger=logging.getLogger("CommandsManager"))
    await cm.start()
    logger.info("CommandsManager started (handler_timeout=%s, compatibility_mode=%s)", cm.handler_timeout, cm.compatibility_mode)

    # Helper: introspect worker state
    def log_active_info(reason: str = ""):
        try:
            info = cm.active_handlers_info()
            logger.debug("ACTIVE INFO (%s): %s", reason, info)
        except Exception:
            logger.exception("Failed to collect active handlers info")

    # Register a deterministic fast hello handler (explicit)
    async def fast_hello_handler(req):
        logger.debug("fast_hello_handler ENTRY (origin=%s raw=%s)", getattr(req, "origin", None), getattr(req, "raw", None))
        # simulate small CPU-bound work
        await asyncio.sleep(0.1)
        msg = f"Hello (fast) from {req.origin}"
        logger.debug("fast_hello_handler EXIT -> %s", msg)
        return (msg, True, None)

    # Register a slow handler to simulate long running work
    async def slow_hello_handler(req):
        logger.debug("slow_hello_handler ENTRY (origin=%s raw=%s)", getattr(req, "origin", None), getattr(req, "raw", None))
        try:
            # sleep longer than manager.handler_timeout to force timeout and cancellation
            await asyncio.sleep(10)
            msg = f"Hello (slow) from {req.origin}"
            logger.debug("slow_hello_handler EXIT -> %s", msg)
            return (msg, True, None)
        except asyncio.CancelledError:
            logger.warning("slow_hello_handler received CancelledError (should have been cancelled by manager)")
            raise

    # Ensure handlers are registered (override defaults)
    cm.register_handler("hello", fast_hello_handler)        # test fast path
    cm.register_handler("hello_slow", slow_hello_handler)   # test slow path

    # Subscribe a diagnostic subscriber to log all CommandResponse objects
    def diag_subscriber(resp):
        try:
            # subscriber may be called from worker context; schedule quick log
            logger.debug("SUBSCRIBER RECEIVED: %s", getattr(resp, "__dict__", resp))
        except Exception:
            logger.exception("Error in subscriber")

    cm.subscribe(diag_subscriber)

    # Test 1: normal hello command
    logger.info("Submitting 'hello' (fast) command")
    fut1 = await cm.submit(origin="test", command="hello")
    log_active_info("after enqueue hello")
    try:
        # wait longer than handler timeout to show manager enforced timeout if it were slow
        resp1 = await asyncio.wait_for(fut1, timeout=5.0)
        logger.info("Received response for 'hello': %s", getattr(resp1, "__dict__", resp1))
    except asyncio.TimeoutError:
        logger.error("UI wait_for timed out for 'hello' (this indicates UI-side timeout)")
        fut1.cancel()
    except Exception:
        logger.exception("Error awaiting 'hello'")

    # Short pause and introspect
    await asyncio.sleep(0.2)
    log_active_info("post-hello completion")

    # Test 2: slow hello; manager's handler_timeout=3.0 should cancel/timeout
    logger.info("Submitting 'hello_slow' (slow) command")
    fut2 = await cm.submit(origin="test", command="hello_slow")
    log_active_info("after enqueue hello_slow")
    try:
        # UI waiting slightly longer than manager timeout, so manager should reply with timeout response
        resp2 = await asyncio.wait_for(fut2, timeout=6.0)
        logger.info("Received response for 'hello_slow': %s", getattr(resp2, "__dict__", resp2))
    except asyncio.TimeoutError:
        logger.error("UI wait_for timed out for 'hello_slow' (UI timeout shorter than manager behavior)")
        fut2.cancel()
    except Exception:
        logger.exception("Error awaiting 'hello_slow'")

    # Wait briefly so manager cleanup finishes
    await asyncio.sleep(0.5)
    log_active_info("post-hello_slow completion")

    # Test 3: submit unknown command to show unknown handler response
    logger.info("Submitting unknown command 'foobar'")
    fut3 = await cm.submit(origin="test", command="foobar")
    try:
        resp3 = await asyncio.wait_for(fut3, timeout=3.0)
        logger.info("Received response for 'foobar': %s", getattr(resp3, "__dict__", resp3))
    except Exception:
        logger.exception("Error awaiting 'foobar'")

    # Final introspection
    log_active_info("final")

    # Stop manager
    await cm.stop()
    logger.info("CommandsManager stopped")

    logger.info("Diagnostics run complete. See the log file for full trace: %s", LOG_FILE)


def main():
    # Run the diagnostic event loop
    try:
        asyncio.run(run_diagnostics())
    except Exception:
        logger.exception("Diagnostics failed to run")
        print("Diagnostics failed; check logs for details.")
    else:
        print(f"Diagnostics finished. Open the log file: {LOG_FILE}")


if __name__ == "__main__":
    main()