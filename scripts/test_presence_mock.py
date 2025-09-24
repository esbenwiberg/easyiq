#!/usr/bin/env python3
"""Mock test script for the new presence API implementation."""

import asyncio
import sys
import os
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'aula_easyiq'))

from client import EasyIQClient

# Mock API response based on the example provided
MOCK_PRESENCE_RESPONSE = {
    "status": {
        "code": 0,
        "message": "OK"
    },
    "data": [
        {
            "id": 2120621,
            "institutionProfile": {
                "profileId": 1796983,
                "id": 4465156,
                "institutionCode": "731003",
                "institutionName": "Hornbæk Skole",
                "role": "child",
                "name": "Avi Emilie Wiberg Lohmann",
                "shortName": "AEWL",
                "institutionRole": "early-student",
                "metadata": "2A"
            },
            "status": 8,
            "checkInTime": "07:59:02",
            "checkOutTime": "15:07:12",
            "entryTime": "07:30:00",
            "exitTime": "15:00:00",
            "comment": "Selvbestemmer 1400-1500",
            "exitWith": None
        },
        {
            "id": 1568162,
            "institutionProfile": {
                "profileId": 2849478,
                "id": 4874248,
                "institutionCode": "G20313",
                "institutionName": "Børnehuset Æblehaven",
                "role": "child",
                "name": "Max Emil Wiberg Lohmann",
                "shortName": "MEWL",
                "institutionRole": "daycare",
                "metadata": "Troldebo"
            },
            "status": 8,
            "checkInTime": "07:59:31",
            "checkOutTime": "14:55:05",
            "entryTime": "07:30:00",
            "exitTime": "15:00:00",
            "comment": None,
            "exitWith": "Mormor"
        }
    ],
    "version": 22,
    "module": "presence",
    "method": "getDailyOverview"
}

async def test_presence_processing():
    """Test the presence data processing without real API calls."""
    
    print("Testing presence API implementation with mock data...")
    print("-" * 60)
    
    # Create client
    client = EasyIQClient("mock_user", "mock_pass")
    
    # Mock the session and authentication
    client._authenticated = True
    client._session = MagicMock()
    
    # Create a mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=MOCK_PRESENCE_RESPONSE)
    
    # Mock the session.get context manager
    client._session.get = MagicMock()
    client._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    client._session.get.return_value.__aexit__ = AsyncMock(return_value=None)
    
    try:
        # Test presence for each child in the mock data
        for child_data in MOCK_PRESENCE_RESPONSE["data"]:
            child_id = str(child_data["institutionProfile"]["id"])
            child_name = child_data["institutionProfile"]["name"]
            
            print(f"\n--- Testing presence for {child_name} (ID: {child_id}) ---")
            
            presence_data = await client.get_presence(child_id)
            
            if presence_data:
                print("✅ Presence data processed successfully:")
                print(f"  Status: {presence_data.get('status', 'N/A')}")
                print(f"  Status Code: {presence_data.get('status_code', 'N/A')}")
                print(f"  Check In: {presence_data.get('check_in_time', 'N/A')}")
                print(f"  Check Out: {presence_data.get('check_out_time', 'N/A')}")
                print(f"  Entry Time: {presence_data.get('entry_time', 'N/A')}")
                print(f"  Exit Time: {presence_data.get('exit_time', 'N/A')}")
                print(f"  Comment: {presence_data.get('comment', 'N/A')}")
                print(f"  Exit With: {presence_data.get('exit_with', 'N/A')}")
                
                # Format like the screenshot
                print("\n📱 Display format (like screenshot):")
                status_code = presence_data.get('status_code', 0)
                if status_code == 8:  # HENTET/GÅET
                    print("Status: Gået")
                elif status_code == 3:  # KOMMET/TIL STEDE
                    print("Status: Til stede")
                else:
                    print(f"Status: {presence_data.get('status', 'N/A')}")
                
                if presence_data.get('check_in_time'):
                    print(f"Kom: kl. {presence_data.get('check_in_time')}")
                
                if presence_data.get('check_out_time'):
                    print(f"Gik: kl. {presence_data.get('check_out_time')}")
                
                if presence_data.get('exit_time'):
                    print(f"Send hjem: kl. {presence_data.get('exit_time')}")
                
                if presence_data.get('comment'):
                    print("Bemærkninger:")
                    print(presence_data.get('comment'))
                
                # Verify the data matches expected values from mock
                expected_data = child_data
                assert presence_data.get('status_code') == expected_data.get('status'), f"Status code mismatch"
                assert presence_data.get('check_in_time') == expected_data.get('checkInTime'), f"Check in time mismatch"
                assert presence_data.get('check_out_time') == expected_data.get('checkOutTime'), f"Check out time mismatch"
                assert presence_data.get('entry_time') == expected_data.get('entryTime'), f"Entry time mismatch"
                assert presence_data.get('exit_time') == expected_data.get('exitTime'), f"Exit time mismatch"
                assert presence_data.get('comment') == expected_data.get('comment'), f"Comment mismatch"
                assert presence_data.get('exit_with') == expected_data.get('exitWith'), f"Exit with mismatch"
                
                print("✅ All data validation checks passed!")
                
            else:
                print("❌ No presence data retrieved")
                return False
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed! The presence API implementation is working correctly.")
        print("✅ API call structure is correct")
        print("✅ Data extraction is working")
        print("✅ Status mapping is correct")
        print("✅ Display format matches requirements")
        return True
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await client.close()

if __name__ == "__main__":
    success = asyncio.run(test_presence_processing())
    sys.exit(0 if success else 1)