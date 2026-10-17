"""Mirelo SFX 2.0 example: give a silent or badly scored video its sound design.

Requires:
    pip install praisonai-tools[mirelo] praisonaiagents
    export MIRELO_API_KEY=sk-...
    export OPENAI_API_KEY=...

Already have a FAL_KEY? The same model is reachable with no extra install:
    from praisonai_tools import FalTool
    FalTool().run_model("mirelo-ai/sfx2.0/video-to-audio",
                        {"video_url": "https://...", "num_samples": 1, "preserve_speech": True})
"""

from praisonaiagents import Agent

from praisonai_tools import mirelo_video_to_sfx

agent = Agent(
    name="sound-designer",
    instructions=(
        "Add sound design to the video the user gives you. "
        "Use 1 variant unless asked otherwise, and report the saved file paths."
    ),
    tools=[mirelo_video_to_sfx],
)

agent.start("Add sound to https://di3otfzjg1gxa.cloudfront.net/chase.mp4 (10 seconds), no music")
