# Method guide template

Copy the skeleton below to `docs/method-guides/<REGISTRY_NAME>.md`, keep every `##` heading in this
order (`tests/test_method_guides.py` checks them) and add the guide to the [index](README.md).

Rules:

- Equations in LaTeX: `$…$` inline, a fenced `math` block for display equations. Use the symbols of
  the source paper and the Python names of [notation.md](../notation.md).
- Separate what the authors published (*Original formulation*) from what the code computes
  (*Repository implementation*). Every departure goes in the **Repository choices** list.
- The worked example must run: every fenced `python` block is executed by the test, and should
  `assert` its numbers against a hand calculation or a published value. Label synthetic data as a
  demonstration, not as validation.
- Do not copy the generated catalogue ([METHODS.md](../../METHODS.md)): link to it.
- Hand-written documentation spells `Böhme`; Python source spells `Boehme`.

````markdown
# <Method name> (`<REGISTRY_NAME>`)

> **Registry name:** `<REGISTRY_NAME>` · **Catalogue entry:** [<ID>](../../METHODS.md#<id>) ·
> **Source:** <Author (year)>, <DOI link> · **Implementation:**
> [`<module>.py`](../../src/multifat/models/<path>.py)

## Overview

Method type (stress-, strain-, energy-based …), family (critical plane, invariant, integral …),
the loading and materials it was proposed for, and its status in the catalogue.

## Original formulation

The criterion as published, with equation numbers, symbols and units, the plane rule (if any) and
the fatigue-limit or life form.

## Repository implementation

What the code computes: damage parameter, plane selection and `_ext` variant, shear amplitude
rule, sign conventions.

**Repository choices**

- Each departure from the source, and why.

## Material constants and inputs

| Symbol | Python / workbook name | Unit | Source | Required |
| --- | --- | --- | --- | --- |

## Calibration

1. The procedure prescribed by the original authors.
2. What the repository does (workbook value, `--constants`, pipeline calibration, fatigue-limit
   dataset) and how it differs.
3. Where the result is recorded and which tests it used.

## Worked example

A small case checkable by hand, run through the public API with `assert`s; then the CLI command
on a supplied workbook and the files to inspect.

## Comparison capabilities and outputs

Life route (master curve or native law), DP comparison route, `_ext` variant, physical meaning
of the CSV values.

## Verification and limitations

Which tests check what, what is not verified, source misprints, validity domain.

## References

Full citations with DOI.
````
