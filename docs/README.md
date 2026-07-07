# Documentation Architecture

This directory contains the design documentation for **Evolution Toy
Universe**.

## Philosophy

Each document focuses on a single architectural concern.

The numbering is intentional and represents a dependency chain rather
than a simple reading order.

    Project Charter
        ↓
    Vision
        ↓
    Core Principles
        ↓
    Simulation Model
        ↓
    World Model
        ↓
    Organism Model
        ↓
    Energy Model
        ↓
    Reproduction
        ↓
    Neural System
        ↓
    User Interface
        ↓
    Technical Design
        ↓
    Roadmap

## Repository Workflow

1.  Discuss ideas in ChatGPT.
2.  Reach a design decision.
3.  Promote the decision into the appropriate Markdown document.
4.  Commit the change to Git.
5.  Generate `design.md` from the individual documents when appropriate.

The Git repository serves as the long-term memory of the project. Chat
conversations are exploratory; the Markdown documents are authoritative.
