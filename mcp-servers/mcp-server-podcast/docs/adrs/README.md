# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the Podcast MCP Server project.

## What are ADRs?

Architecture Decision Records (ADRs) are documents that capture an important architectural decision made, along with its context and consequences. They provide a record of the reasoning behind significant architectural choices.

## ADRs for this project

- [ADR Template](./0000-adr-template.md) - Template for creating new ADRs

## Inherited ADRs from Podcastly

These ADRs from the original Podcastly project are carried forward as architectural guidance:

- [0001-clean-architecture-with-protocols.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0001-clean-architecture-with-protocols.md) - Use of Python Protocols for clean architecture
- [0002-asyncio-first-approach.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0002-asyncio-first-approach.md) - Asyncio-first approach for concurrency
- [0003-dependency-injection-pattern.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0003-dependency-injection-pattern.md) - Use of dependency injection pattern
- [0004-domain-models-with-dataclasses.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0004-domain-models-with-dataclasses.md) - Domain models with dataclasses
- [0005-output-filename-generation.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0005-output-filename-generation.md) - Output filename generation strategy
- [0006-azure-managed-identities.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0006-azure-managed-identities.md) - Use of Azure Managed Identities
- [0007-speech-services-rest-api.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0007-speech-services-rest-api.md) - Use of Speech Services REST API
- [0008-prompt-engineering-approach.md](https://github.com/robotdad/podcast/blob/main/docs/adrs/0008-prompt-engineering-approach.md) - Prompt engineering approach

## Creating a new ADR

1. Copy `0000-adr-template.md` to `NNNN-title-with-dashes.md` where `NNNN` is the next number in sequence
2. Fill in the template with your decision, including context, decision, alternatives considered, and consequences
3. Update this README.md to add a link to your new ADR
4. Submit the ADR for review as part of a pull request