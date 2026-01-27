# Common Issues & Solutions - Manim Jupyter Workflow
**Last Updated:** January 27, 2026

This document catalogs known issues and their solutions to prevent repetition in future projects.

---

## 🔴 CRITICAL ISSUES (Must Fix Before Running)

### Issue 1: ModuleNotFoundError - style_utils not found

**Symptom:**
```python
ModuleNotFoundError: No module named 'style_utils'
```

**Cause:** Jupyter notebook not recognizing modules in current directory (Windows path issue)

**Solution:** Add absolute path to Cell 1 BEFORE imports:
```python
import sys
sys.path.append(r'C:\Users\Computer\Documents\GitHub\MathTex\Visualizations')

# Then import
from manim import *
from style_utils import *
```

**Status:** ✅ Fixed in template v2.0

---

### Issue 2: ParsingError in manim.cfg

**Symptom:**
```python
ParsingError: Source contains parsing errors: WindowsPath('manim.cfg')
[line 11]: '```\n'
```

**Cause:** Copied markdown formatting (```, ---) into config file

**Solution:** Remove ALL markdown syntax. Config file must be plain INI format:
```ini
[CLI]
media_dir = C:\Users\Computer\Documents\GitHub\MathTex\Visualizations\media
video_dir = {media_dir}/videos

[output]
verbosity = WARNING
```

**NEVER include:**
- ❌ Backticks (```)
- ❌ Markdown headers (##, ---)
- ❌ Code fence markers

**Status:** ✅ Documented in template

---

### Issue 3: Videos Saving to Wrong Directory

**Symptom:** Videos end up in Jupyter temp folder or unexpected locations

**Cause:** Manim not configured with correct working directory

**Solution:** Set environment variables and working directory in Cell 1:
```python
BASE_DIR = r'C:\Users\Computer\Documents\GitHub\MathTex\Visualizations'
os.chdir(BASE_DIR)
os.environ['MANIM_OUTPUT_DIR'] = os.path.join(BASE_DIR, 'media')
config.output_file = "project_name"  # Sets folder name
```

**Result:** Videos save to `media/videos/project_name/720p30/`

**Status:** ✅ Fixed in template v2.0

---

## ⚠️ COMMON ERRORS (Easy to Avoid)

### Issue 4: Duplicate Magic Command Error

**Symptom:**
```python
UsageError: Line magic function `%%manim` not found
```

**Cause:** Magic command (`%%manim`) appears twice in cell or in wrong location

**Solution:**
- Magic command must be **FIRST LINE** of cell (no spaces before)
- Only ONE magic command per cell
- Format: `%%manim -qm -v WARNING SceneName`

**Status:** ✅ Fixed with consolidated scene block in v2.0

---

### Issue 5: Grid Overlapping Title

**Symptom:** Vectors or axes appear on top of title text

**Cause:** NumberPlane Y-range exceeds safe zone (Y > 3.0)

**Solution:** Use `self.get_standard_grid()` from BaseScene:
```python
grid = self.get_standard_grid()  # Automatically respects safe zones
```

Or manually limit Y-range:
```python
axes = NumberPlane(
    y_range=[-3.5, 3.5, 1],  # Never exceed 3.5
    # ...
)
axes.shift(DOWN * 0.5)  # Shift to content zone
```

**Status:** ✅ Enforced in BaseScene class

---

### Issue 6: Text Unreadable Over Grid

**Symptom:** Labels disappear or hard to read on grid lines

**Cause:** Text placed directly over grid without background

**Solution:** Always add background rectangle:
```python
label = MathTex(r"\vec{a}", font_size=LABEL_SIZE)
label.add_background_rectangle(buff=0.1, opacity=0.9)
```

**Status:** ✅ Built into `add_vector_with_label()` helper

---

## 📦 DEPENDENCY ISSUES

### Issue 7: MoviePy Import Failure

**Symptom:**
```python
ModuleNotFoundError: No module named 'moviepy.editor'
```

**Cause:** MoviePy installation issues on Windows

**Solution:** **DO NOT USE MOVIEPY**. Use FFmpeg directly instead:
```python
subprocess.run([
    "ffmpeg", "-f", "concat", "-safe", "0", 
    "-i", "concat_list.txt", "-c", "copy", "output.mp4"
])
```

FFmpeg is already required by Manim, so no new dependencies.

**Status:** ✅ Template v2.0 uses FFmpeg only

---

## 🎬 VIDEO CONCATENATION

### Issue 8: FFmpeg Not Found

**Symptom:**
```python
FileNotFoundError: [WinError 2] The system cannot find the file specified
```

**Cause:** FFmpeg not in system PATH

**Solution:**
1. Check if FFmpeg exists: `where ffmpeg` in Command Prompt
2. If not installed, download from https://ffmpeg.org/
3. Add to PATH or use full path in subprocess call

**Alternative:** Use Windows Video Editor (built-in, no dependencies)

**Status:** ✅ Template includes fallback message

---

## 🔧 WORKFLOW ISSUES

### Issue 9: Confusing Output Directory Names

**Symptom:** Videos save to `media/videos/Visualizations/` instead of project name

**Cause:** Jupyter notebook filename becomes folder name

**Solution:** Either:
1. Rename notebook to match project (e.g., `dot_product.ipynb`)
2. OR force project name: `config.output_file = "dot_product"`

**Recommended:** Use method 2 (force project name in Cell 1)

**Status:** ✅ Fixed in template v2.0

---

### Issue 10: Kernel Needs Restart After Config Changes

**Symptom:** Changes to `manim.cfg` or imports not taking effect

**Cause:** Jupyter caches imports and config

**Solution:** **Kernel → Restart Kernel** after:
- Editing `manim.cfg`
- Modifying `style_utils.py`
- Changing any imports

**Status:** ⚠️ User awareness required

---

## 📋 CHECKLIST FOR NEW PROJECTS

Before running any scenes:

- [ ] Cell 1 includes absolute path: `sys.path.append(r'C:\...\Visualizations')`
- [ ] `manim.cfg` has NO markdown formatting (no ```, no ---)
- [ ] Cell 1 sets `config.output_file = "project_name"`
- [ ] All scenes use `BaseScene` class
- [ ] Grids use `self.get_standard_grid()`
- [ ] All labels have `.add_background_rectangle()`
- [ ] Magic commands are first line: `%%manim -qm -v WARNING SceneName`
- [ ] FFmpeg concatenation script uses project name

---

## 🚀 QUICK DEBUG COMMANDS

Add these to a cell for troubleshooting:

```python
# Verify paths
import os
print("Working directory:", os.getcwd())
print("Python path:", sys.path[:3])
print("Files in directory:", os.listdir())

# Verify Manim config
from manim import config
print("Manim output dir:", config.output_file)
print("Quality:", config.quality)

# Find generated videos
for root, dirs, files in os.walk("media"):
    for file in files:
        if file.endswith('.mp4'):
            print(f"Found: {os.path.join(root, file)}")
```

---

## 📝 NOTES FOR AI GENERATION

When generating new projects:

1. **ALWAYS** review this document first
2. **DO NOT** suggest moviepy for concatenation
3. **DO NOT** create separate blocks for each scene (consolidate)
4. **ALWAYS** include absolute path in Cell 1
5. **ALWAYS** set `config.output_file` in Cell 1
6. **ALWAYS** use `BaseScene.get_standard_grid()`
7. **ALWAYS** add backgrounds to text over grids
8. **ALWAYS** provide FFmpeg concatenation script

---

**End of Common Issues Document**
