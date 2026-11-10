# 51 — The references of a table in the report

**Status:** done
**Type:** feature
**Priority:** low
**Area:** Report
**Summary:** The report writes the references of a table as running text, those to it without their key, cardinality or coverage, and nothing shows at a glance which tables a table is connected to.

## The problem

Below its columns, a table of the report has two paragraphs on its references: `References:`, each
with its column, the key it refers to, its cardinality, its coverage and whether it is given, and
`Referred to by:`, each with the table and the column that refers alone. Both are lists run together
by `·`:

- A table of many references gives a block of text that is hard to read or compare.
- What is said of a reference differs by its direction: of those to the table, the report does not
  say which of its keys is referred to, how many rows refer, how much is covered or whether it is
  given, though the profile holds all of it.
- Which tables a table is connected to, and in which direction, has to be pieced together from both.

## What is wanted

- **Two tables**, of the references going out of the table and of those coming in, in place of the
  two paragraphs, each with its own columns:
  - Out: column, table referred to, key, cardinality, coverage, given.
  - In: table that refers, its column, key of this table, cardinality, coverage, given.
- **A diagram below them**: the table in the centre, every table connected to it around it.

## Considerations

The report is one HTML document with its styles inside and no script, so that it can be sent and
printed as it is ([12](12-the-stage-report.md)). The diagram is to keep that.

- **An SVG in the document, its layout computed when the report is written.** Needs no script, no
  library and no network, prints sharply, and takes the colours of the style sheet. Its boxes can be
  links to the sections of the tables, `#table-<name>`, which the contents of the report already
  use. The layout has to be written by us, and the width of a name can only be estimated, without a
  browser to measure it. Proposed.
- **A library drawing it in the browser, such as Mermaid.** Gives a layout for free, but is a
  script, of a size that outweighs the report or fetched from the network.
- **Graphviz, rendering the SVG when the report is written.** Gives a good layout, but is a program
  to install beside the tool, for a layout as simple as this one.
- **Boxes of CSS alone.** Needs no drawing, but has no lines between them, which are the point.

How the proposed diagram is laid out:

- **Two sides rather than a circle.** The tables that refer on the left, the table in the centre,
  the tables referred to on the right, arrows from left to right. Direction reads at a glance, the
  names of the boxes do not run into each other, and a table of many neighbours only makes the
  diagram taller. A circle of 30 neighbours has no room for their names.
- **One box per connected table,** however many references run to it; the columns are in the tables
  above. Whether a line says how many references it stands for is to be seen.
- **Cases to settle:** a table that both refers and is referred to by the same table; a table
  referring to itself; a hub of very many neighbours; no diagram for a table of no references.
- **The templates stay escaping.** Geometry is computed in Python, names are written by the
  template, so that autoescaping keeps covering them; the SVG is not built as a string.

To be decided with the interface, before anything is built:

- Whether reference candidates join the table of references going out, told apart, or stay the
  paragraph they are, and whether the diagram shows them, dashed, or the references alone.
- Original names in the boxes, as the references are written today, or harmonized ones.
- Who owns the layout: `report`, or a module of its own if it outgrows the sentence of `report`.

## Done when

- The references going out of a table and those coming in are each a table of the report, a table
  without any showing none of the two.
- Below them, a diagram shows the table and every table connected to it, by direction, in a document
  that still holds no script and prints.
- `docs/ARCHITECTURE.md` says so where it describes the report.

## History

- **2026-11-10** — Opened at the request of the maintainer.
- **2026-11-10** — Done, as the maintainer decided: reference candidates are dashed in the diagram
  and stay the paragraph they are below the references, and the boxes hold original names. The
  layout is computed in `report`, the SVG written by the template. Of a table referring to itself,
  the diagram draws a loop on its box; a table that both refers and is referred to stands on each
  side; a side shows twenty tables and the number of the others. `Profile.candidates_referring` is
  new, beside `Profile.referring`, as the diagram shows the candidates coming in as well. A line
  stands for a connected table and says nothing of how many references it is; the columns are in
  the tables above it.
- **2026-11-10** — After the review, as the maintainer decided: the layout is the module `diagram`,
  not a part of `report`, which gathers the connections from the profile and has `diagram` lay them
  out; `Profile.candidates_referring` stays as it is, rather than one method for the connections.
