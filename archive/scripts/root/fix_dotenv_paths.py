import glob
import os

files = glob.glob("src/laptopfinder/runners/hunter/*.py")

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()
    
    # replace load_dotenv() with load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    if "from pathlib import Path" not in content:
        content = content.replace("from dotenv import load_dotenv", "from pathlib import Path\nfrom dotenv import load_dotenv")
    content = content.replace("load_dotenv()", 'load_dotenv(Path(__file__).resolve().parents[3] / ".env")')
    
    with open(filepath, "w") as f:
        f.write(content)

# For ebay_hunter.py (parents[2])
with open("src/laptopfinder/runners/ebay_hunter.py", "r") as f:
    content = f.read()
if "from pathlib import Path" not in content:
    content = content.replace("from dotenv import load_dotenv", "from pathlib import Path\nfrom dotenv import load_dotenv")
content = content.replace("load_dotenv()", 'load_dotenv(Path(__file__).resolve().parents[2] / ".env")')
with open("src/laptopfinder/runners/ebay_hunter.py", "w") as f:
    f.write(content)

