#!/usr/bin/env python
"""Ollama configuration and setup helper for Snaglist Pro.

Sets up Ollama endpoint, downloads models, and verifies connectivity.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional

OLLAMA_DEFAULT = "http://localhost:11434"
OLLAMA_TEXT_MODEL = "llama3.2"
CONFIG_FILE = Path.home() / ".snaglist_pro" / "ollama_config.json"


def get_ollama_config() -> Dict:
    """Load Ollama configuration from file or env."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    
    return {
        "url": os.getenv("OLLAMA_URL", OLLAMA_DEFAULT),
        "text_model": os.getenv("OLLAMA_TEXT_MODEL", OLLAMA_TEXT_MODEL),
        "enabled": os.getenv("AI_ENABLED", "true").lower() == "true",
    }


def save_ollama_config(config: Dict) -> None:
    """Save Ollama configuration."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✓ Configuration saved to {CONFIG_FILE}")


def test_connection(url: str) -> bool:
    """Test connectivity to Ollama."""
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def pull_model(url: str, model: str) -> bool:
    """Pull a model from Ollama."""
    print(f"\nPulling model: {model}")
    try:
        with requests.post(
            f"{url}/api/pull",
            json={"name": model},
            stream=True,
            timeout=300,
        ) as resp:
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "%" in status:
                        print(f"  {status}", end="\r")
            print(f"✓ {model} pulled successfully")
            return True
    except Exception as e:
        print(f"✗ Pull failed: {e}")
        return False


def interactive_setup() -> Dict:
    """Interactive Ollama setup."""
    print("\n=== Snaglist Pro — Ollama Configuration ===\n")
    
    config = get_ollama_config()
    
    url = input(f"Ollama URL [{config['url']}]: ").strip() or config["url"]
    config["url"] = url
    
    print(f"\nTesting connection to {url}...")
    if test_connection(url):
        print("✓ Connected!")
    else:
        print("✗ Could not reach Ollama. Make sure it's running:")
        print("  1. Download from https://ollama.ai")
        print("  2. Run: ollama serve")
        sys.exit(1)
    
    model = input(f"\nText model [{config['text_model']}]: ").strip() or config["text_model"]
    config["text_model"] = model
    
    print(f"\nDownloading {model}...")
    if pull_model(url, model):
        print(f"✓ Model ready!")
        config["enabled"] = True
    else:
        resp = input("Skip model download? [y/N]: ").strip().lower()
        config["enabled"] = resp != "y"
    
    save_ollama_config(config)
    return config


def cli_main():
    """CLI entrypoint."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        config = get_ollama_config()
        
        if cmd == "test":
            url = sys.argv[2] if len(sys.argv) > 2 else config["url"]
            if test_connection(url):
                print(f"✓ Connected to {url}")
            else:
                print(f"✗ Cannot reach {url}")
                sys.exit(1)
        
        elif cmd == "pull":
            model = sys.argv[2] if len(sys.argv) > 2 else config["text_model"]
            if pull_model(config["url"], model):
                sys.exit(0)
            else:
                sys.exit(1)
        
        elif cmd == "config":
            print(json.dumps(config, indent=2))
        
        elif cmd == "disable":
            config["enabled"] = False
            save_ollama_config(config)
            print("✓ AI disabled")
        
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python ollama_helper.py [test|pull|config|disable|setup]")
            sys.exit(1)
    else:
        interactive_setup()


if __name__ == "__main__":
    cli_main()
