#!/usr/bin/env python3
"""
Test script to verify Azure OpenAI configuration with multi-deployment support
"""

import os
import sys
from esperanto import AIFactory

def test_azure_configuration():
    """Test Azure OpenAI configuration with the new setup."""

    print("🔍 Testing Azure OpenAI Configuration")
    print("=" * 50)

    # Check required environment variables
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nSet these environment variables:")
        print("export AZURE_OPENAI_API_KEY=your-key")
        print("export AZURE_OPENAI_ENDPOINT=https://thefoundry.openai.azure.com/")
        print("export AZURE_OPENAI_API_VERSION=2025-04-01-preview")
        return False

    print("✅ Required environment variables present")

    # Check deployment configurations
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not chat_deployment:
        print("⚠️  No chat deployment configured. Set AZURE_OPENAI_CHAT_DEPLOYMENT or AZURE_OPENAI_DEPLOYMENT_NAME")
    else:
        print(f"✅ Chat deployment configured: {chat_deployment}")

    if not embedding_deployment:
        print("⚠️  No embedding deployment configured. Set AZURE_OPENAI_EMBEDDING_DEPLOYMENT or AZURE_OPENAI_DEPLOYMENT_NAME")
    else:
        print(f"✅ Embedding deployment configured: {embedding_deployment}")

    # Test provider availability
    try:
        print("\n🔍 Checking provider availability...")
        available_providers = AIFactory.get_available_providers()

        if "azure" in available_providers.get("language", []):
            print("✅ Azure language model provider available")
        else:
            print("❌ Azure language model provider not available")

        if "azure" in available_providers.get("embedding", []):
            print("✅ Azure embedding provider available")
        else:
            print("❌ Azure embedding provider not available")

    except Exception as e:
        print(f"⚠️  Could not check provider availability: {e}")

    # Test model creation (if deployments are configured)
    if chat_deployment:
        try:
            print(f"\n🧪 Testing language model creation...")
            llm = AIFactory.create_language(
                model_name=chat_deployment,
                provider="azure"
            )
            print(f"✅ Language model created successfully: {llm.__class__.__name__}")
        except Exception as e:
            print(f"❌ Failed to create language model: {e}")

    if embedding_deployment:
        try:
            print(f"\n🧪 Testing embedding model creation...")
            embedder = AIFactory.create_embedding(
                model_name=embedding_deployment,
                provider="azure"
            )
            print(f"✅ Embedding model created successfully: {embedder.__class__.__name__}")
        except Exception as e:
            print(f"❌ Failed to create embedding model: {e}")

    print("\n📋 Configuration Summary:")
    print(f"  Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"  API Version: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    print(f"  Chat Deployment: {chat_deployment or 'Not configured'}")
    print(f"  Embedding Deployment: {embedding_deployment or 'Not configured'}")

    return True

if __name__ == "__main__":
    success = test_azure_configuration()
    sys.exit(0 if success else 1)