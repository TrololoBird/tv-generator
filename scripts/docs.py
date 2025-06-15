from pathlib import Path
from src.docs.readme_generator import generate_readme

if __name__ == "__main__":
    out = generate_readme(Path("README.md"))
    print(f"\u2713 {out}")
