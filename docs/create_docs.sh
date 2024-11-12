#!/bin/bash

# Create documentation directory structure
mkdir -p docs/{installation,api,development,deployment,guides}

# Create installation documentation
cat > docs/installation/README.md << 'EOF'
# Installation Guide

## Prerequisites

### System Requirements
- CPU: 2+ cores recommended
- RAM: 4GB minimum, 8GB recommended
- Storage: 20GB minimum
- Operating System: Ubuntu 20.04+ / Windows 10+ / macOS 10.15+

[Rest of installation content...]
EOF

# Create API documentation
cat > docs/api/README.md << 'EOF'
# API Documentation

## Authentication
All API endpoints except `/token` require authentication using JWT tokens.

[Rest of API content...]
EOF

# Create development documentation
cat > docs/development/README.md << 'EOF'
# Development Guide

## Setup Development Environment

[Rest of development content...]
EOF

# Create deployment documentation
cat > docs/deployment/README.md << 'EOF'
# Deployment Guide

## Docker Deployment

[Rest of deployment content...]
EOF

# Create FAQ
cat > docs/guides/FAQ.md << 'EOF'
# Frequently Asked Questions

## General Questions

[FAQ content...]
EOF

# Create Known Issues
cat > docs/guides/KNOWN_ISSUES.md << 'EOF'
# Known Issues

## Current Issues

[Known issues content...]
EOF

# Create Contributing Guide
cat > docs/guides/CONTRIBUTING.md << 'EOF'
# Contributing Guide

## How to Contribute

[Contributing content...]
EOF

# Create main README
cat > docs/README.md << 'EOF'
# SMS Bridge Documentation

Welcome to the SMS Bridge documentation. This documentation will help you install, configure, and use the SMS Bridge system.

## Contents

1. [Installation Guide](installation/README.md)
2. [API Documentation](api/README.md)
3. [Development Guide](development/README.md)
4. [Deployment Guide](deployment/README.md)

## Additional Resources

- [FAQ](guides/FAQ.md)
- [Known Issues](guides/KNOWN_ISSUES.md)
- [Contributing Guide](guides/CONTRIBUTING.md)

## Quick Start

See the [Installation Guide](installation/README.md) for getting started quickly.

## Support

If you need help, please:
1. Check the FAQ
2. Search existing issues
3. Create a new issue if needed
EOF

# Make script executable
chmod +x create_docs.sh 