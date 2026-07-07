# 00 - Project Charter

## Documentation Strategy

The project documentation is intentionally divided into a series of
focused design documents.

The numbering represents a **dependency order**, not merely a table of
contents. Lower-numbered documents define concepts that later documents
build upon.

**Guiding rules**

-   Lower-numbered documents should not depend on higher-numbered
    documents.
-   Higher-numbered documents may reference concepts defined earlier.
-   The repository is the authoritative source for project knowledge.
-   ChatGPT conversations are working sessions whose conclusions should
    be promoted into the appropriate Markdown document.
-   `design.md` is an assembled/master document generated from these
    source documents and should not be edited directly.

### Documentation Structure

``` text
docs/
├── README.md
├── 00-project-charter.md
├── 01-vision.md
├── 02-core-principles.md
├── 03-simulation-model.md
├── 04-world-model.md
├── 05-organism-model.md
├── 06-energy-model.md
├── 07-reproduction.md
├── 08-neural-system.md
├── 09-ui.md
├── 10-technical-design.md
├── 11-roadmap.md
├── 12-philosophy.md
├── design.md        # Generated master document
│
├── adr/
│   ├── ADR-0001-...
│   └── ...
│
└── assets/
    ├── diagrams/
    ├── images/
    └── animations/
```
