# n8n Python Code Node - Test Script
# Paste this into a Python Code node to verify packages are working
#
# Requires subprocess in N8N_RUNNERS_STDLIB_ALLOW for ImageMagick tests.
# If subprocess is not allowed, remove those sections.

import subprocess

# Test imports
import requests
import PIL
from PIL import Image
import pandas as pd
import numpy as np
import io
import base64

results = {
    "packages": {},
    "tests": {}
}

# Package versions
results["packages"] = {
    "requests": requests.__version__,
    "pillow": PIL.__version__,
    "pandas": pd.__version__,
    "numpy": np.__version__,
}

# Test 1: NumPy array operations
arr = np.array([1, 2, 3, 4, 5])
results["tests"]["numpy_sum"] = int(np.sum(arr))
results["tests"]["numpy_mean"] = float(np.mean(arr))

# Test 2: Pandas DataFrame
df = pd.DataFrame({
    "name": ["Alice", "Bob", "Charlie"],
    "score": [85, 92, 78]
})
results["tests"]["pandas_rows"] = len(df)
results["tests"]["pandas_mean_score"] = float(df["score"].mean())

# Test 3: Pillow - create a simple test image
img = Image.new("RGB", (100, 100), color="blue")
buffer = io.BytesIO()
img.save(buffer, format="PNG")
img_base64 = base64.b64encode(buffer.getvalue()).decode()
results["tests"]["pillow_image_created"] = True
results["tests"]["pillow_image_size"] = len(img_base64)

# Test 4: Requests (httpbin echo)
try:
    resp = requests.get("https://httpbin.org/get", timeout=5)
    results["tests"]["requests_status"] = resp.status_code
    results["tests"]["requests_ok"] = resp.ok
except Exception as e:
    results["tests"]["requests_error"] = str(e)

# Test 5: ImageMagick (via subprocess - requires subprocess in STDLIB_ALLOW)
try:
    proc = subprocess.run(
        ["magick", "--version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    version_line = proc.stdout.split("\n")[0] if proc.stdout else "unknown"
    results["tests"]["imagemagick_version"] = version_line
    results["tests"]["imagemagick_available"] = proc.returncode == 0
except Exception as e:
    results["tests"]["imagemagick_error"] = str(e)

# Test 6: GraphicsMagick
try:
    proc = subprocess.run(
        ["gm", "version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    version_line = proc.stdout.split("\n")[0] if proc.stdout else "unknown"
    results["tests"]["graphicsmagick_version"] = version_line
    results["tests"]["graphicsmagick_available"] = proc.returncode == 0
except Exception as e:
    results["tests"]["graphicsmagick_error"] = str(e)

# Test 7: ffmpeg
try:
    proc = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    version_line = proc.stdout.split("\n")[0] if proc.stdout else "unknown"
    results["tests"]["ffmpeg_version"] = version_line
    results["tests"]["ffmpeg_available"] = proc.returncode == 0
except Exception as e:
    results["tests"]["ffmpeg_error"] = str(e)

return results
