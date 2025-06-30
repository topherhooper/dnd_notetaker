# D&D Notetaker Documentation

This directory contains comprehensive documentation for the D&D Notetaker project and its audio extraction service.

## Documentation Index

### Audio Extract Service

- **[Audio Extract Deployment Guide](./audio-extract-deployment-guide.md)**
  - Complete deployment process from development to production
  - Docker, GitHub Actions, and GCSfuse integration
  - Monitoring and maintenance procedures
  - Troubleshooting common issues

### Architecture Documentation

- **[CLAUDE-architecture.md](../CLAUDE-architecture.md)**
  - System architecture overview
  - Component descriptions
  - Database schemas
  - API documentation

### Testing Documentation

- **[CLAUDE-tests.md](../tests/CLAUDE-tests.md)**
  - Test suite overview
  - Testing strategies
  - How to run tests
  - Writing new tests

### Planning Documents

The `planning-docs/` directory contains feature planning and design documents:

- **[modularize-june282025.md](../planning-docs/modularize-june282025.md)**
  - Audio extract service modularization
  - Production enhancement plan
  - Dashboard improvements
  - GitHub Actions and GCSfuse integration

## Quick Links

### For Developers

1. [Local Development Setup](./audio-extract-deployment-guide.md#local-development)
2. [Running Tests](../audio_extract/README.md#testing)
3. [CI/CD Pipeline](./audio-extract-deployment-guide.md#cicd-pipeline)

### For Operations

1. [Production Deployment](./audio-extract-deployment-guide.md#production-deployment)
2. [Monitoring Guide](./audio-extract-deployment-guide.md#monitoring-and-maintenance)
3. [Troubleshooting](./audio-extract-deployment-guide.md#troubleshooting)

### For Users

1. [Audio Extract README](../audio_extract/README.md)
2. [Dashboard Guide](../audio_extract/dashboard/README.md)
3. [Configuration Examples](../audio_extract/audio_extract_config.dev.yaml)

## Contributing

When adding new documentation:

1. Follow the existing structure and naming conventions
2. Update this README with links to new documents
3. Keep documentation close to the code it describes
4. Use clear, concise language
5. Include practical examples

## Documentation Standards

- Use Markdown for all documentation
- Include a table of contents for long documents
- Add code examples with syntax highlighting
- Keep line length under 120 characters
- Update documentation when code changes

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-org/dnd_notetaker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/dnd_notetaker/discussions)
- **Email**: support@example.com