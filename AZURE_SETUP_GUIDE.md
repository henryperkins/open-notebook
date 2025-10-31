# Azure OpenAI Setup Guide for Open Notebook

This guide covers the setup of Azure OpenAI with **multi-deployment support** using the latest Esperanto library (v2.8.0).

## 🚀 Quick Setup

### 1. Environment Variables

Set these environment variables in your shell or `.env` file:

```bash
# Core Azure Configuration
export AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
export AZURE_OPENAI_ENDPOINT=https://thefoundry.openai.azure.com/
export AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Multi-deployment configuration
export AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-mini
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```

### 2. Azure AI Studio Deployment Names

**⚠️ Important**: You must have these deployments created in your Azure AI Studio:

- **Chat Deployment**: `gpt-5-mini` (GPT-5 Mini model)
- **Embedding Deployment**: `text-embedding-3-large` (Text Embedding 3 Large model)

If your deployments have different names, update the environment variables accordingly:

```bash
export AZURE_OPENAI_CHAT_DEPLOYMENT=your-chat-deployment-name
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your-embedding-deployment-name
```

### 3. Configuration in Open Notebook

1. **Start Open Notebook**
2. **Go to Settings → Models**
3. **Add Models**:
   - **Language Model**:
     - Name: `gpt-5-mini`
     - Provider: `azure`
     - Type: `language`
   - **Embedding Model**:
     - Name: `text-embedding-3-large`
     - Provider: `azure`
     - Type: `embedding`

4. **Set Defaults**:
   - Default Chat Model: `gpt-5-mini`
   - Default Embedding Model: `text-embedding-3-large`

## 🔧 Advanced Configuration

### Multi-Deployment Environment Variables

The new Esperanto v2.8.0 supports deployment-specific configurations:

```bash
# Language Model Configuration
AZURE_OPENAI_API_KEY_LLM=your-key
AZURE_OPENAI_ENDPOINT_LLM=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION_LLM=2025-04-01-preview

# Embedding Model Configuration
AZURE_OPENAI_API_KEY_EMBEDDING=your-key
AZURE_OPENAI_ENDPOINT_EMBEDDING=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION_EMBEDDING=2025-04-01-preview
```

### Configuration Priority

1. **Deployment-specific variables** (e.g., `AZURE_OPENAI_API_KEY_LLM`)
2. **Generic variables** (e.g., `AZURE_OPENAI_API_KEY`)
3. **Error if neither found**

## 🧪 Testing Configuration

Run the test script to verify your setup:

```bash
python test_azure_config.py
```

Expected output:
```
✅ Required environment variables present
✅ Chat deployment configured: gpt-5-mini
✅ Embedding deployment configured: text-embedding-3-large
✅ Azure language model provider available
✅ Azure embedding provider available
✅ Language model created successfully
✅ Embedding model created successfully
```

## 📋 Configuration Summary

Your final configuration should be:

| Setting | Value |
|---------|-------|
| **API Version** | `2025-04-01-preview` |
| **Chat Model** | `gpt-5-mini` |
| **Embedding Model** | `text-embedding-3-large` |
| **Endpoint** | `https://thefoundry.openai.azure.com/` |
| **Provider** | `azure` |

## 🚨 Troubleshooting

### Common Issues

**1. Deployment Not Found**
```
Error: Deployment not found
```
- Solution: Check deployment names in Azure AI Studio
- Ensure deployments are in the same resource as your endpoint

**2. API Version Issues**
```
Error: Invalid API version
```
- Solution: Verify `2025-04-01-preview` is supported in your region
- Try `2024-12-01-preview` if needed

**3. Authentication Issues**
```
Error: Invalid API key
```
- Solution: Check API key has correct permissions
- Ensure key is not expired

### Debug Commands

```bash
# Check environment variables
echo "API Key: $AZURE_OPENAI_API_KEY"
echo "Endpoint: $AZURE_OPENAI_ENDPOINT"
echo "API Version: $AZURE_OPENAI_API_VERSION"
echo "Chat Deployment: $AZURE_OPENAI_CHAT_DEPLOYMENT"
echo "Embedding Deployment: $AZURE_OPENAI_EMBEDDING_DEPLOYMENT"

# Test Azure endpoint
curl -H "api-key: $AZURE_OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     "$AZURE_OPENAI_ENDPOINT/openai/deployments?api-version=$AZURE_OPENAI_API_VERSION"
```

## 📚 Additional Resources

- [Azure OpenAI Documentation](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [Open Notebook AI Models Guide](docs/features/ai-models.md)
- [Esperanto Library Documentation](https://github.com/lfnovo/esperanto)

## ✅ Verification Checklist

- [ ] Azure OpenAI resource created
- [ ] `gpt-5-mini` deployment created
- [ ] `text-embedding-3-large` deployment created
- [ ] Environment variables set
- [ ] Test script passes
- [ ] Models added in Open Notebook Settings
- [ ] Default models configured
- [ ] Chat functionality tested
- [ ] Search/embedding functionality tested