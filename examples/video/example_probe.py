"""Example: Probe video metadata."""
import sys
sys.path.insert(0, "/Users/praison/PraisonAI-tools/praisonai_tools/video")

from probe import probe_video

result = probe_video("/Users/praison/Agent-Recipes/agent_recipes/input.mov")

print(f"Duration: {result.duration}s")
print(f"Resolution: {result.width}x{result.height}")
print(f"FPS: {result.fps}")
print(f"Codec: {result.codec}")
