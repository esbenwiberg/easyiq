#!/usr/bin/env python3
"""
Interactive debugging helper for EasyIQ integration.
This script provides a menu-driven interface for common debugging tasks.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file."""
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value

def check_token_state():
    """Check if optional MitID token state is set."""
    required = {
        "EASYIQ_MITID_USERNAME": os.getenv("EASYIQ_MITID_USERNAME"),
        "EASYIQ_ACCESS_TOKEN": os.getenv("EASYIQ_ACCESS_TOKEN"),
        "EASYIQ_REFRESH_TOKEN": os.getenv("EASYIQ_REFRESH_TOKEN"),
        "EASYIQ_TOKEN_EXPIRES_AT": os.getenv("EASYIQ_TOKEN_EXPIRES_AT"),
    }
    
    print("🔐 Checking MitID token state...")
    missing = [key for key, value in required.items() if not value]
    if missing:
        print("❌ Optional live smoke token state not found!")
        print("   Fill MitID token fields in .env only when running live smoke tests")
        print(f"   Missing: {', '.join(missing)}")
        return False
    
    print(f"✅ MitID username: {required['EASYIQ_MITID_USERNAME']}")
    print("✅ Aula token fields are present")
    return True

def check_file_structure():
    """Check if all required files exist."""
    print("📁 Checking file structure...")
    
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    required_files = [
        "custom_components/aula_easyiq/__init__.py",
        "custom_components/aula_easyiq/manifest.json",
        "custom_components/aula_easyiq/const.py",
        "custom_components/aula_easyiq/client.py",
        "custom_components/aula_easyiq/config_flow.py",
        "custom_components/aula_easyiq/sensor.py",
        "custom_components/aula_easyiq/binary_sensor.py",
        "custom_components/aula_easyiq/calendar.py",
    ]
    
    all_good = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING!")
            all_good = False
    
    return all_good

def validate_json_files():
    """Validate JSON configuration files."""
    print("🔍 Validating JSON files...")
    
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    json_files = [
        "custom_components/aula_easyiq/manifest.json",
        "custom_components/aula_easyiq/strings.json",
        "custom_components/aula_easyiq/translations/en.json",
    ]
    
    all_valid = True
    for json_file in json_files:
        full_path = project_root / json_file
        try:
            with open(full_path) as f:
                json.load(f)
            print(f"✅ {json_file}")
        except FileNotFoundError:
            print(f"❌ {json_file} - NOT FOUND!")
            all_valid = False
        except json.JSONDecodeError as e:
            print(f"❌ {json_file} - INVALID JSON: {e}")
            all_valid = False
    
    return all_valid

def test_python_syntax():
    """Test Python syntax of integration files."""
    print("🐍 Testing Python syntax...")
    
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    python_files = [
        "custom_components/aula_easyiq/__init__.py",
        "custom_components/aula_easyiq/const.py",
        "custom_components/aula_easyiq/client.py",
        "custom_components/aula_easyiq/config_flow.py",
        "custom_components/aula_easyiq/sensor.py",
        "custom_components/aula_easyiq/binary_sensor.py",
        "custom_components/aula_easyiq/calendar.py",
    ]
    
    all_valid = True
    for py_file in python_files:
        full_path = project_root / py_file
        try:
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(full_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {py_file}")
            else:
                print(f"❌ {py_file} - SYNTAX ERROR:")
                print(f"   {result.stderr}")
                all_valid = False
        except Exception as e:
            print(f"❌ {py_file} - ERROR: {e}")
            all_valid = False
    
    return all_valid

def run_client_test():
    """Run the standalone client test."""
    print("🧪 Running client test...")
    try:
        # Get the current script directory and project root
        current_script_dir = Path(__file__).parent
        project_root = current_script_dir.parent
        script_path = current_script_dir / "test_client.py"
        
        print(f"Debug: Current script dir: {current_script_dir}")
        print(f"Debug: Project root: {project_root}")
        print(f"Debug: Script path: {script_path}")
        
        if not script_path.exists():
            print(f"❌ Script not found at: {script_path}")
            return False
        
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=str(project_root), encoding='utf-8', errors='replace')
        
        print("STDOUT:")
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Client test passed!")
            return True
        else:
            print("❌ Client test failed!")
            return False
    except Exception as e:
        print(f"❌ Error running client test: {e}")
        return False

def show_integration_status():
    """Show current integration status."""
    print("📊 Integration Status:")
    print("-" * 50)
    
    # Check optional live token state
    token_state_ok = check_token_state()
    print()
    
    # Check file structure
    files_ok = check_file_structure()
    print()
    
    # Validate JSON
    json_ok = validate_json_files()
    print()
    
    # Test Python syntax
    syntax_ok = test_python_syntax()
    print()
    
    # Overall status
    print("📋 Summary:")
    print(f"   MitID token state: {'✅' if token_state_ok else '❌'}")
    print(f"   File Structure: {'✅' if files_ok else '❌'}")
    print(f"   JSON Files: {'✅' if json_ok else '❌'}")
    print(f"   Python Syntax: {'✅' if syntax_ok else '❌'}")
    
    if all([files_ok, json_ok, syntax_ok]):
        print("\n🎉 Everything looks good! Ready for testing.")
        return True
    else:
        print("\n⚠️  Some issues found. Please fix them before testing.")
        return False

def show_menu():
    """Show the main debugging menu."""
    print("\n" + "="*60)
    print("🔧 EasyIQ Integration Debug Helper")
    print("="*60)
    print("1. Check Integration Status")
    print("2. Test API Client (Standalone)")
    print("3. Validate MitID Token State")
    print("4. Check File Structure")
    print("5. Validate JSON Files")
    print("6. Test Python Syntax")
    print("7. Start Development Server")
    print("8. View Debug Tips")
    print("9. Exit")
    print("-" * 60)

def show_debug_tips():
    """Show debugging tips."""
    print("\n💡 Debug Tips:")
    print("-" * 40)
    print("• Run ./scripts/validate.sh before live smoke testing")
    print("• Check logs in terminal when running dev server")
    print("• Use Home Assistant web UI: Settings → System → Logs")
    print("• Look for 'custom_components.aula_easyiq' in logs")
    print("• Check entity states in Developer Tools → States")
    print("• Restart Home Assistant after code changes")
    print("• Use DEBUGGING.md for detailed troubleshooting")

def start_dev_server():
    """Start the development server."""
    print("🚀 Starting development server...")
    
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    # Use the Python script which is most reliable
    script_path = project_root / "scripts" / "dev_start.py"
    
    if script_path.exists():
        print(f"Running: {script_path}")
        print("Press Ctrl+C to stop the server")
        print("Web interface: http://localhost:8123")
        print("-" * 40)
        
        try:
            subprocess.run([sys.executable, str(script_path)], cwd=str(project_root))
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
    else:
        print(f"❌ Script not found: {script_path}")

def main():
    """Main debugging interface."""
    # Load environment variables
    load_env_file()
    
    while True:
        show_menu()
        
        try:
            choice = input("Select option (1-9): ").strip()
            
            if choice == "1":
                show_integration_status()
            elif choice == "2":
                run_client_test()
            elif choice == "3":
                check_token_state()
            elif choice == "4":
                check_file_structure()
            elif choice == "5":
                validate_json_files()
            elif choice == "6":
                test_python_syntax()
            elif choice == "7":
                start_dev_server()
            elif choice == "8":
                show_debug_tips()
            elif choice == "9":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid option. Please choose 1-9.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
