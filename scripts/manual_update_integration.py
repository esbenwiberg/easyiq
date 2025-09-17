#!/usr/bin/env python3
"""
Manual update EasyIQ integration files
This script copies files to ha-config directory when Docker is not available
"""

import shutil
from pathlib import Path

def main():
    """Manually copy integration files to ha-config directory."""
    print("📁 Manual EasyIQ Integration Update")
    print("=" * 40)
    
    source_dir = Path("custom_components/aula_easyiq")
    target_dir = Path("ha-config/custom_components/aula_easyiq")
    
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "translations").mkdir(exist_ok=True)
    
    files_to_copy = [
        "__init__.py",
        "sensor.py", 
        "client.py",
        "calendar.py",
        "binary_sensor.py",
        "manifest.json",
        "config_flow.py",
        "const.py",
        "strings.json",
        "services.yaml"
    ]
    
    # Copy main files
    for file_name in files_to_copy:
        source_file = source_dir / file_name
        target_file = target_dir / file_name
        
        if source_file.exists():
            shutil.copy2(source_file, target_file)
            print(f"✅ Copied {file_name}")
        else:
            print(f"⚠️  File not found: {file_name}")
    
    # Copy translations
    trans_source = source_dir / "translations" / "en.json"
    trans_target = target_dir / "translations" / "en.json"
    
    if trans_source.exists():
        shutil.copy2(trans_source, trans_target)
        print("✅ Copied translations/en.json")
    else:
        print("⚠️  Translation file not found")
    
    print("\n✅ Manual copy completed!")
    print("📋 Next steps:")
    print("1. Restart Home Assistant (if using Docker: docker restart homeassistant)")
    print("2. Check http://localhost:8123")
    print("3. Go to Settings → Devices & Services → EasyIQ")

if __name__ == "__main__":
    main()