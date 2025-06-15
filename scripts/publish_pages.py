from pathlib import Path
import shutil
import subprocess
import tempfile
import argparse


def publish_pages(branch: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir(parents=True, exist_ok=True)
        for spec_file in Path("specs").glob("*.yaml"):
            shutil.copy2(spec_file, spec_dir / spec_file.name)
        bundle_file = Path("bundle.yaml")
        if bundle_file.exists():
            shutil.copy2(bundle_file, spec_dir / bundle_file.name)
        links = "".join(
            f'<li><a href="specs/{f.name}">{f.name}</a></li>'
            for f in spec_dir.glob("*.yaml")
        )
        (tmp_path / "index.html").write_text(f"<ul>{links}</ul>", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(["git", "checkout", "-b", branch], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Publish specs to GitHub Pages"],
            cwd=tmp_path,
            check=True,
        )
        try:
            remote = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "push", remote, f"HEAD:{branch}", "--force"],
                cwd=tmp_path,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Git push failed") from exc
    print(f"\u2713 Published to {branch}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", default="gh-pages")
    args = parser.parse_args()
    publish_pages(args.branch)
