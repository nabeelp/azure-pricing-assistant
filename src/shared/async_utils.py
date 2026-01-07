"""Async helpers to control event loop shutdown noise from MCP streams."""

import asyncio
from typing import Any, Coroutine, Dict, TypeVar

T = TypeVar("T")


def suppress_async_generator_errors(
    loop: asyncio.AbstractEventLoop, context: Dict[str, Any]
) -> None:
    """
    Ignore shutdown errors caused by MCP's streamable HTTP client cleanup.

    AnyIO can raise a spurious "Attempted to exit cancel scope" RuntimeError when
    MCP streamable HTTP generators are cancelled during loop teardown. Filtering
    those here keeps shutdown quiet while letting other exceptions surface.
    """
    message = context.get("message", "") or ""
    exception = context.get("exception")

    if "streamablehttp_client" in message:
        return

    if exception:
        exc_text = str(exception)
        if "streamablehttp_client" in exc_text or "cancel scope" in exc_text:
            return

    loop.default_exception_handler(context)


def create_event_loop() -> asyncio.AbstractEventLoop:
    """Create an event loop with the shutdown error filter attached."""
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(suppress_async_generator_errors)
    return loop


def run_coroutine(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run a coroutine on a fresh event loop while suppressing MCP shutdown noise.

    This mirrors asyncio.run but adds the custom exception handler and a guarded
    shutdown sequence so generator cleanup errors do not leak to stderr.
    """
    loop = create_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        finally:
            asyncio.set_event_loop(None)
            loop.close()
