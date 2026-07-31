"""
AI Quant Bootstrap — Cross-platform installer.
Run: python install.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run(cmd: list[str], description: str) -> bool:
    print(f"\n{'='*55}")
    print(f"  {description}")
    print(f"{'='*55}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Done.")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed.")
        return False

def main():
    print("=" * 55)
    print("  AI Quant Bootstrap — Installer")
    print("=" * 55)
    print()

    # Check Python
    print(f"[1/3] Python version: {sys.version}")
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required. Please upgrade.")
        sys.exit(1)
    
    # Create venv (optional on Windows, helpful on Linux/Mac)
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print("\n[2/3] Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Created.")
    else:
        print("\n[2/3] Virtual environment already exists.")
    
    # Determine pip path
    if os.name == "nt":  # Windows
        pip_path = str(venv_dir / "Scripts" / "pip.exe")
        python_path = str(venv_dir / "Scripts" / "python.exe")
    else:
        pip_path = str(venv_dir / "bin" / "pip")
        python_path = str(venv_dir / "bin" / "python")

    # Install dependencies
    print(f"\n[3/3] Installing dependencies...")
    run([pip_path, "install", "--upgrade", "pip"], "Upgrading pip")
    run([pip_path, "install", "-r", "requirements.txt"], "Installing packages")
    
    # Check config
    if not Path("config.yaml").exists():
        print("\n⚠️  config.yaml not found. Please create it from the template.")
    else:
        print("\n✅ config.yaml found.")
    
    print()
    print("=" * 55)
    print("  INSTALLATION COMPLETE!")
    print("=" * 55)
    print()
    print("Next steps:")
    if os.name == "nt":
        print(f"  1. Activate venv:  {venv_dir}\\Scripts\\activate")
    else:
        print(f"  1. Activate venv:  source {venv_dir}/bin/activate")
    print("  2. Edit config.yaml — add your API keys")
    print("  3. Run:            python launcher.py")
    print()

if __name__ == "__main__":
    main()