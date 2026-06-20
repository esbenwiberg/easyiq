#!/usr/bin/env python3
"""
Validate EasyIQ integration for Home Assistant compatibility.
This script checks if the integration meets HA requirements.
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

def validate_manifest():
    """Validate manifest.json file."""
    print("🔍 Validating manifest.json...")
    
    manifest_path = Path("custom_components/aula_easyiq/manifest.json")
    if not manifest_path.exists():
        print("❌ manifest.json not found")
        return False
    
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_fields = ["domain", "name", "version", "documentation", "dependencies", "codeowners", "requirements"]
        missing_fields = [field for field in required_fields if field not in manifest]
        
        if missing_fields:
            print(f"❌ Missing required fields in manifest.json: {missing_fields}")
            return False
        
        print("✅ manifest.json is valid")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in manifest.json: {e}")
        return False

def validate_init_file():
    """Validate __init__.py file."""
    print("🔍 Validating __init__.py...")
    
    init_path = Path("custom_components/aula_easyiq/__init__.py")
    if not init_path.exists():
        print("❌ __init__.py not found")
        return False
    
    try:
        # Try to import the module
        spec = importlib.util.spec_from_file_location("easyiq", init_path)
        module = importlib.util.module_from_spec(spec)
        
        # Check for required functions
        with open(init_path) as f:
            content = f.read()
        
        if "async_setup" not in content:
            print("❌ async_setup function not found in __init__.py")
            return False
        
        print("✅ __init__.py is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating __init__.py: {e}")
        return False

def validate_config_flow():
    """Validate config_flow.py file."""
    print("🔍 Validating config_flow.py...")
    
    config_flow_path = Path("custom_components/aula_easyiq/config_flow.py")
    if not config_flow_path.exists():
        print("❌ config_flow.py not found")
        return False
    
    try:
        with open(config_flow_path) as f:
            content = f.read()
        
        required_elements = [
            "ConfigFlow",
            "async_step_user",
            "validate_input"
        ]
        
        missing_elements = [elem for elem in required_elements if elem not in content]
        
        if missing_elements:
            print(f"❌ Missing required elements in config_flow.py: {missing_elements}")
            return False
        
        print("✅ config_flow.py is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating config_flow.py: {e}")
        return False

def validate_sensor():
    """Validate sensor.py file."""
    print("🔍 Validating sensor.py...")
    
    sensor_path = Path("custom_components/aula_easyiq/sensor.py")
    if not sensor_path.exists():
        print("❌ sensor.py not found")
        return False
    
    try:
        with open(sensor_path) as f:
            content = f.read()
        
        required_elements = [
            "async_setup_entry",
            "SensorEntity",
            "state",
            "extra_state_attributes"
        ]
        
        missing_elements = [elem for elem in required_elements if elem not in content]
        
        if missing_elements:
            print(f"❌ Missing required elements in sensor.py: {missing_elements}")
            return False
        
        print("✅ sensor.py is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating sensor.py: {e}")
        return False

def validate_translations():
    """Validate translation files."""
    print("🔍 Validating translations...")
    
    strings_path = Path("custom_components/aula_easyiq/strings.json")
    translations_path = Path("custom_components/aula_easyiq/translations/en.json")
    
    if not strings_path.exists():
        print("❌ strings.json not found")
        return False
    
    if not translations_path.exists():
        print("❌ translations/en.json not found")
        return False
    
    try:
        with open(strings_path) as f:
            strings = json.load(f)
        
        with open(translations_path) as f:
            translations = json.load(f)
        
        # Check if translations match strings
        if strings != translations:
            print("⚠️  strings.json and translations/en.json don't match")
        
        print("✅ Translation files are valid")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in translation files: {e}")
        return False

def validate_file_structure():
    """Validate overall file structure."""
    print("🔍 Validating file structure...")
    
    required_files = [
        "custom_components/aula_easyiq/__init__.py",
        "custom_components/aula_easyiq/manifest.json",
        "custom_components/aula_easyiq/config_flow.py",
        "custom_components/aula_easyiq/sensor.py",
        "custom_components/aula_easyiq/client.py",
        "custom_components/aula_easyiq/const.py",
        "custom_components/aula_easyiq/migration.py",
        "custom_components/aula_easyiq/mitid_auth.py",
        "custom_components/aula_easyiq/views.py",
        "custom_components/aula_easyiq/strings.json",
        "custom_components/aula_easyiq/translations/en.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ File structure is valid")
    return True

def validate_mitid_auth_shape():
    """Validate MitID/token auth replaced password setup."""
    print("🔍 Validating MitID auth shape...")

    manifest = json.loads(Path("custom_components/aula_easyiq/manifest.json").read_text())
    requirements = " ".join(manifest.get("requirements", []))
    after_dependencies = manifest.get("after_dependencies", [])

    if "http" not in after_dependencies:
        print("❌ manifest.json must load after the Home Assistant http integration")
        return False

    if "requests" not in requirements:
        print("❌ manifest.json must declare requests for Aula token refresh")
        return False

    config_flow = Path("custom_components/aula_easyiq/config_flow.py").read_text()
    client = Path("custom_components/aula_easyiq/client.py").read_text()

    required_config_flow_terms = [
        "CONF_MITID_USERNAME",
        "async_external_step",
        "build_config_entry_data",
    ]
    missing_terms = [term for term in required_config_flow_terms if term not in config_flow]
    if missing_terms:
        print(f"❌ Config flow missing MitID terms: {missing_terms}")
        return False

    if "login.aula.dk/auth/login.php" in client or "selectedIdp" in client:
        print("❌ Client still contains old form-login scraping")
        return False

    user_facing_files = [
        "README.md",
        "DEVELOPMENT_SETUP.md",
        ".env.template",
        "scripts/dev_setup.py",
        "scripts/docker_setup.py",
        "scripts/test_client.py",
        "custom_components/aula_easyiq/strings.json",
        "custom_components/aula_easyiq/translations/en.json",
    ]
    forbidden_terms = [
        "Unilogin password",
        "username/password",
        "EASYIQ_PASSWORD",
        "your_aula_password",
        "Aula credentials",
        "username and password",
    ]

    violations = []
    for file_name in user_facing_files:
        content = Path(file_name).read_text()
        for term in forbidden_terms:
            if term in content:
                violations.append(f"{file_name}: {term}")

    if violations:
        print(f"❌ Old password setup text remains: {violations}")
        return False

    print("✅ MitID auth shape is valid")
    return True

def main():
    """Run all validation checks."""
    print("🏠 Home Assistant Integration Validation")
    print("=" * 50)
    
    # Change to project root directory
    os.chdir(Path(__file__).parent.parent)
    
    checks = [
        validate_file_structure,
        validate_manifest,
        validate_init_file,
        validate_config_flow,
        validate_sensor,
        validate_translations,
        validate_mitid_auth_shape,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Error running {check.__name__}: {e}")
            results.append(False)
        print()
    
    # Summary
    print("📊 Validation Summary")
    print("=" * 20)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} checks passed!")
        print("🎉 Integration is ready for Home Assistant!")
        return True
    else:
        print(f"❌ {total - passed} out of {total} checks failed")
        print("🔧 Please fix the issues above before deploying")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
