"""Render loop helper with bounded retries."""

import asyncio
from typing import Callable, Awaitable, Any
from .protocols import RenderResult


async def render_iterate(
    write_fn: Callable[..., Awaitable[Any]],
    lint_fn: Callable[..., Awaitable[Any]],
    render_fn: Callable[..., Awaitable[RenderResult]],
    patch_fn: Callable[[str], Awaitable[Any]],
    max_retries: int = 3,
    **kwargs
) -> RenderResult:
    """Bounded write → lint → render → patch loop.
    
    This helper implements the standard motion graphics authoring loop:
    1. Write HTML/GSAP composition
    2. Lint for common issues
    3. Render to MP4
    4. If render fails, patch the composition and retry
    
    Args:
        write_fn: Function to write initial composition
        lint_fn: Function to lint composition  
        render_fn: Function to render composition to MP4
        patch_fn: Function to patch composition based on error
        max_retries: Maximum number of retry attempts
        **kwargs: Arguments passed to write_fn
        
    Returns:
        RenderResult with final render status
    """
    last_error = ""
    
    for attempt in range(max_retries + 1):
        try:
            # Step 1: Write composition
            if attempt == 0:
                await write_fn(**kwargs)
            
            # Step 2: Lint composition
            lint_result = await lint_fn()
            if not lint_result.ok:
                # Lint failed - try to patch
                lint_error = "; ".join(lint_result.messages)
                await patch_fn(f"Lint errors: {lint_error}")
                continue
            
            # Step 3: Render composition
            render_result = await render_fn()
            
            if render_result.ok:
                # Success!
                return render_result
            
            # Render failed - prepare for retry
            last_error = render_result.stderr
            
            if attempt < max_retries:
                # Try to patch based on error
                await patch_fn(f"Render error: {last_error}")
            
        except Exception as e:
            last_error = str(e)
            
            if attempt < max_retries:
                # Try to patch based on exception
                await patch_fn(f"Exception: {last_error}")
            
    # All retries exhausted
    return RenderResult(
        ok=False,
        output_path=None,
        bytes_=None,
        stderr=f"Failed after {max_retries} retries. Last error: {last_error}",
        size_kb=0
    )