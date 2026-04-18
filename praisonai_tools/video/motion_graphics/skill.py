"""Compact HTML/GSAP authoring skill for motion graphics agents."""

MOTION_GRAPHICS_SKILL = """
# Motion Graphics Authoring Skill

You create deterministic, frame-perfect HTML/CSS/GSAP compositions for video export.

## Required HTML Structure

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <style>
        body { margin: 0; padding: 0; background: #000; overflow: hidden; }
        #stage { width: 1920px; height: 1080px; position: relative; }
    </style>
</head>
<body>
    <div id="stage" data-duration="5.0">
        <!-- Your animated elements here -->
    </div>
    
    <script>
        // Create timeline
        const tl = gsap.timeline({ paused: true });
        
        // Add animations
        tl.to(".element", { duration: 1, x: 100, ease: "power2.out" })
          .to(".element", { duration: 0.5, scale: 1.2 }, "-=0.2");
        
        // Required: Export timeline
        window.__timelines = [tl];
    </script>
</body>
</html>
```

## Critical Rules

1. **Deterministic**: No Math.random(), Date.now(), or any non-deterministic functions
2. **Finite**: No infinite loops or repeat: -1 
3. **Timeline Export**: Must set window.__timelines = [tl]
4. **Duration Attribute**: Add data-duration to stage element
5. **Paused Timeline**: Always create with { paused: true }
6. **Fixed Viewport**: Use 1920x1080 stage size

## Animation Guidelines

- Use transform properties (x, y, scale, rotation) for smooth animation
- Avoid animating width, height, visibility, display
- Use opacity for fade effects
- Prefer ease functions: "power2.out", "back.out", "elastic.out"
- Chain animations with timeline positioning: "-=0.5", "+=1"
- Keep total duration under 60 seconds

## Text Animations

```javascript
// Split text for word/character animation
tl.to(".title .word", { 
    duration: 0.8, 
    y: 0, 
    opacity: 1, 
    stagger: 0.1,
    ease: "power3.out" 
});
```

## Shape Animations

```javascript
// Animate SVG paths
tl.fromTo("#path", 
    { drawSVG: "0%" },
    { duration: 2, drawSVG: "100%", ease: "power2.inOut" }
);
```

## Common Patterns

- Fade in: `{ opacity: 0 }` to `{ opacity: 1 }`
- Slide in: `{ x: -100 }` to `{ x: 0 }`  
- Scale up: `{ scale: 0 }` to `{ scale: 1 }`
- Stagger: Use stagger property for multiple elements

## Performance

- Keep element count under 100
- Use CSS transforms, not absolute positioning
- Minimize DOM queries - store references
- Use timeline labels for complex sequences

## Debugging

- Add data-debug="true" to stage for visual timeline scrubber
- Use tl.duration() to verify total duration matches data-duration
- Test with tl.seek(time) at key moments

Write complete, working HTML files. Test all animations before export.
"""