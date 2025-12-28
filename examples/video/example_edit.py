"""Example: Full video editing pipeline."""
import sys
sys.path.insert(0, "/Users/praison/PraisonAI-tools/praisonai_tools/video")

from pipeline import edit_video

result = edit_video(
    input_path="/Users/praison/Agent-Recipes/agent_recipes/input.mov",
    output_path="/tmp/edited_example.mp4",
    preset="podcast",
    remove_fillers=True,
    remove_repetitions=True,
    remove_silence=True,
    verbose=True,
)

if result.success:
    print(f"Success! Output: {result.output_path}")
    print(f"Artifacts: {result.artifacts}")
else:
    print(f"Failed: {result.error}")
