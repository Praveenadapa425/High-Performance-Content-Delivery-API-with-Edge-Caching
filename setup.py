#!/usr/bin/env python3
"""
Quick setup and run script for the Content Delivery API.
Use this to quickly set up and run the project locally.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command and report status."""
    print(f"\n📍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=False)
        print(f"✅ {description} complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False


def check_python():
    """Check Python version."""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ required")
        return False
    return True


def check_docker():
    """Check if Docker is available."""
    result = subprocess.run("docker --version", shell=True, capture_output=True)
    if result.returncode == 0:
        print("✅ Docker is available")
        return True
    else:
        print("⚠️  Docker not found (optional)")
        return False


def main():
    print("=" * 80)
    print("🚀 HIGH-PERFORMANCE CONTENT DELIVERY API - SETUP")
    print("=" * 80)
    
    # Check Python
    print("\n[1] Checking Python installation...")
    if not check_python():
        sys.exit(1)
    
    # Check Docker
    print("\n[2] Checking Docker installation...")
    has_docker = check_docker()
    
    # Install dependencies
    print("\n[3] Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt", "Dependency installation"):
        sys.exit(1)
    
    # Create .env file if not exists
    print("\n[4] Setting up environment file...")
    if not os.path.exists(".env"):
        run_command("cp .env.example .env", "Creating .env file")
        print("📝 Edit .env file to configure your settings")
    else:
        print("✅ .env file already exists")
    
    # Option for Docker Compose or manual setup
    print("\n[5] Choose your setup method:")
    if has_docker:
        print("  1. Docker Compose (Recommended) - Starts API + PostgreSQL + MinIO")
        print("  2. Manual setup - Requires manual PostgreSQL and MinIO")
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            print("\n🐳 Starting Docker Compose stack...")
            if run_command("docker-compose up -d", "Docker Compose startup"):
                print("\n✅ Stack is running!")
                print("  - API: http://localhost:8000")
                print("  - PostgreSQL: localhost:5432")
                print("  - MinIO: http://localhost:9000")
                
                print("\n[6] Initializing database...")
                run_command("python scripts/init_db.py", "Database initialization")
            sys.exit(0)
    
    # Manual setup
    print("\n🔧 Manual setup mode")
    print("Please ensure you have running:")
    print("  - PostgreSQL on localhost:5432")
    print("  - MinIO on localhost:9000")
    
    # Initialize database
    print("\n[6] Initializing database...")
    if not run_command("python scripts/init_db.py", "Database initialization"):
        print("⚠️  Database initialization may have failed")
    
    # Ready to run
    print("\n" + "=" * 80)
    print("✅ SETUP COMPLETE!")
    print("=" * 80)
    print("\n🚀 To start the API server, run:")
    print("  python -m uvicorn app.main:app --reload")
    print("\n📚 Then access:")
    print("  - API: http://localhost:8000")
    print("  - Swagger Docs: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("\n🧪 To run tests:")
    print("  pytest tests/ -v")
    print("\n⚡ To run benchmark:")
    print("  python scripts/benchmark.py")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
