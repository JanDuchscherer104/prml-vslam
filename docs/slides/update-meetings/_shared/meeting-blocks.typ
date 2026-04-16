#import "../../template.typ": *
#import "team.typ" as team
#import "@preview/booktabs:0.0.4": *

#let placeholder_status_rows = (
  ([...], [], []),
  ([], [], []),
)

#let status_table_slide(
  title: [],
  rows: (),
  ..args,
) = slide(title: title, ..args)[
  #show: booktabs-default-table-style
  #show table.cell.where(y: 0): set text(weight: "bold")
  #align(center)[
    #table(
      columns: (auto, auto, auto),
      align: (left, left, left),
      inset: (x: 0.4em, y: 0.28em),
      toprule(),
      table.header([WP-ID], [Member], [Description]),
      midrule(),
      ..rows.flatten(),
      bottomrule(),
    )
  ]
]

#let meeting_detail_slide(
  items,
  title: [],
  body,
) = slide(
  title: title,
  footer: project_footer(
    footer_authors: team.team_members_footer,
    footer_label: [Update Meetings],
    footer_date: [#items.at(2).display("[day padding:none]. [month repr:short] [year]")],
  ),
)[#body]
