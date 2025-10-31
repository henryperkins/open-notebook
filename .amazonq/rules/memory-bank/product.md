# Open Notebook - Product Overview

## Purpose
Open Notebook is a privacy-focused, self-hosted alternative to Google's Notebook LM. It empowers users to organize research materials, generate AI-powered insights, and create professional podcasts while maintaining complete control over their data.

## Core Value Proposition
- **Privacy First**: Self-hosted solution with no cloud dependencies - your research stays under your control
- **Multi-Model Flexibility**: Support for 16+ AI providers (OpenAI, Anthropic, Ollama, Google, LM Studio, Groq, Mistral, DeepSeek, xAI, OpenRouter, and more)
- **Cost Control**: Choose cheaper AI providers or run completely locally with Ollama
- **No Vendor Lock-in**: Switch providers, deploy anywhere, own your data

## Key Features

### Content Management
- **Multi-Notebook Organization**: Manage multiple research projects simultaneously
- **Universal Content Support**: PDFs, videos, audio files, web pages, Office documents (Word, PowerPoint), and more
- **Intelligent Search**: Full-text and vector search across all content
- **Three-Column Interface**: Sources, Notes, and Chat panels for efficient workflow

### AI-Powered Capabilities
- **Context-Aware Chat**: AI conversations powered by your research materials with proper citations
- **AI-Assisted Notes**: Generate insights or write notes manually
- **Content Transformations**: Powerful customizable actions to summarize and extract insights from sources
- **Reasoning Model Support**: Full support for thinking models like DeepSeek-R1 and Qwen3

### Professional Podcast Generation
- **Multi-Speaker Podcasts**: 1-4 speakers with custom profiles (vs Google's 2-speaker limitation)
- **Episode Profiles**: Reusable podcast templates with custom instructions
- **Full Script Control**: Complete customization of podcast content and style

### Advanced Features
- **Fine-Grained Context Control**: Three levels of control over what AI models can access
- **Comprehensive REST API**: Full programmatic access for custom integrations
- **Optional Password Protection**: Secure public deployments with authentication
- **Cross-Platform Deployment**: Docker, cloud, or local installation options

## Target Users
- **Researchers**: Academics and professionals managing extensive research materials
- **Content Creators**: Podcasters and writers needing AI-assisted content generation
- **Privacy-Conscious Users**: Individuals requiring complete data sovereignty
- **Organizations**: Teams needing self-hosted AI research tools
- **Developers**: Users wanting to customize and extend functionality via REST API

## Use Cases
- Academic research organization and analysis
- Professional podcast creation from research materials
- Knowledge management for teams and individuals
- Content summarization and insight extraction
- Multi-source research synthesis
- Private AI-powered note-taking and analysis

## Competitive Advantages vs Google Notebook LM
- Complete data sovereignty (self-hosted)
- 16+ AI provider choices vs single provider
- 1-4 podcast speakers vs 2 speakers only
- Full REST API vs no API access
- Open source and customizable vs closed system
- Transparent cost control vs subscription model
- Deploy anywhere vs Google-hosted only

## Technical Architecture Highlights

### Graph Database Design
- **SurrealDB**: Multi-model database combining document, graph, and key-value stores
- **Relationship Edges**: Native graph relationships (reference, artifact, refers_to)
- **Record IDs**: Typed identifiers with table prefixes (e.g., source:123)
- **Vector Search**: Built-in support for semantic search with embeddings

### AI Processing Pipeline
- **LangGraph Workflows**: Stateful multi-step AI processing
- **Content Extraction**: Unified pipeline for PDFs, videos, audio, web pages
- **Transformation System**: Pluggable content transformations with insights
- **Embedding Strategy**: Chunked vectorization with atomic database updates
- **Background Jobs**: Async processing via surreal-commands

### Frontend Architecture
- **Next.js App Router**: Modern React with server-side rendering
- **TanStack Query**: Sophisticated server state management with caching
- **Radix UI**: Accessible, unstyled component primitives
- **Tailwind CSS**: Utility-first styling with custom design system
- **Type Safety**: End-to-end TypeScript with Zod validation
