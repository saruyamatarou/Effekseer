"""Entry point for the runtime owned by the Effekseer editor."""
import os
import sys
import threading


def watch_editor():
    # The pipe closes on both normal exit and an editor crash.
    sys.stdin.buffer.read()
    os._exit(0)


if __name__ == "__main__":
    if os.getenv("EFFEKSEER_MCP_MANAGED") == "1":
        threading.Thread(target=watch_editor, daemon=True).start()
    from effekseer_mcp.server import main

    main()
