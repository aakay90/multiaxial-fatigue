# Scientific review dossiers

These dossiers record source-specific scientific assessments for proposed WG4.3 methods. A dossier is a specification and developer handoff, not evidence that a criterion has been implemented or experimentally validated.

| Method | Review | Decision |
| --- | --- | --- |
| [N04, Susmel and Lazzarin (2002)](N04-susmel/README.md) | [Catalogue entry](../../METHODS.md#n04) | READY FOR RESTRICTED IMPLEMENTATION |

Each review directory contains a Markdown handoff (`README.md`), authoritative mathematical formulation (`<method-id>-<method-name>.tex`), traceable citations (`references.bib`), independent machine-readable checks (`benchmarks.json`), and a PDF compiled from the LaTeX source. Preserve source-specific assumptions, numerical reference values, and unresolved scientific decisions. The PDF is a reading copy, not a separate formulation.

To rebuild N04, install `latexmk`, `pdflatex`, `bibtex`, and the LaTeX packages listed in its [handoff](N04-susmel/README.md#build-and-integration), then run:

```bash
cd docs/scientific-reviews/N04-susmel
latexmk -pdf -interaction=nonstopmode -halt-on-error N04-susmel.tex
```

`latexmk` runs BibTeX and repeat LaTeX passes. Temporary build files are ignored by Git. Validate all dossier structures and benchmark JSON files with `python tools/check_scientific_reviews.py` from the repository root.
