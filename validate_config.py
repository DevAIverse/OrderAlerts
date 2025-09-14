#!/usr/bin/env python3
"""
Configuration validation script for Order Alerts
"""
import os
from dotenv import load_dotenv

def validate_config():
    load_dotenv()
    
    required_vars = [
        "CEREBRAS_API_KEY",
        "TELEGRAM_BOT_TOKEN", 
        "TELEGRAM_CHAT_ID"
    ]
    
    optional_vars = [
        "BSE_API_URL",
        "BSE_PDF_BASE_URL_LIVE", 
        "BSE_PDF_BASE_URL_HIST",
        "CEREBRAS_MODEL",
        "TELEGRAM_BOT_TOKEN_2",
        "TELEGRAM_CHAT_ID_2",
        "MIN_MKCAP",
        "MAX_MKCAP", 
        "POLL_INTERVAL"
    ]
    
    print("🔍 Validating configuration...")
    
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_required.append(var)
        else:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
    
    if missing_required:
        print(f"\n❌ Missing required variables: {', '.join(missing_required)}")
        return False
    
    print(f"\n📋 Optional variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: Not set (using default)")
    
    print(f"\n✅ Configuration validation passed!")
    return True

if __name__ == "__main__":
    validate_config()