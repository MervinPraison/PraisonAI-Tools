# Video CLI

```bash
python -m praisonai_tools.video probe input.mp4
```

```bash
python -m praisonai_tools.video probe input.mp4 --output probe.json
```

```bash
python -m praisonai_tools.video probe input.mp4 --json
```

```bash
python -m praisonai_tools.video transcribe input.mp4
```

```bash
python -m praisonai_tools.video transcribe input.mp4 --output transcript.srt
```

```bash
python -m praisonai_tools.video transcribe input.mp4 --format txt --output transcript.txt
```

```bash
python -m praisonai_tools.video transcribe input.mp4 --format json --output transcript.json
```

```bash
python -m praisonai_tools.video transcribe input.mp4 --local
```

```bash
python -m praisonai_tools.video plan input.mp4
```

```bash
python -m praisonai_tools.video plan input.mp4 --output plan.json
```

```bash
python -m praisonai_tools.video plan input.mp4 --preset podcast
```

```bash
python -m praisonai_tools.video plan input.mp4 --no-fillers --no-repetitions
```

```bash
python -m praisonai_tools.video render input.mp4 --timeline plan.json --output output.mp4
```

```bash
python -m praisonai_tools.video render input.mp4 --timeline plan.json --output output.mp4 --reencode
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --preset podcast
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --preset meeting
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --preset course
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --preset clean
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --no-fillers
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --no-repetitions
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --no-silence
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --tangents
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --target-length 6m
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --captions srt
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --captions burn
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --captions off
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --force
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --provider openai
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --provider local
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --no-llm
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --model gpt-4o
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --whisper-model large-v3
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --local
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --reencode
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --verbose
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --workdir ./artifacts
```

```bash
python -m praisonai_tools.video edit input.mp4 --output edited.mp4 --no-artifacts
```
