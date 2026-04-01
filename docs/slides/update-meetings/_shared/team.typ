#let team_members_inline = [
  Florian Beck, Valentin Bumeder, Lukas Röß, Christopher Kirschner, Jan Duchscherer
]

#let team_members_footer = [
  F. Beck, V. Bumeder, L. Röß, C. Kirschner, J. Duchscherer
]

#let team_leader = [Valentin Bumeder]

#let leader_note = [
  *Team Leader:* #team_leader

  - Coordinates the project scope, weekly alignment, and contribution hand-offs.
  - Responsible for limiting over-engineering and scope creep by keeping the team focused.
  - Monitors and adjusts workload distribution.
  - Keeps the work-package split and reporting surfaces aligned across slides and report.
  - Responsible for uploading the weekly update slides.
  - Tries to keep the best overview of the different work packages and the overall project status.
  - Provides mental support.
]

#let placeholder_card_body() = block(
  width: 100%,
  height: 150pt,
  fill: rgb("d9d9d9"),
  inset: 0pt,
)[
  #align(center + horizon)[#text(size: 18pt)[Image]]
]

#let profile_card_body(path) = block(
  width: 100%,
  height: 175pt,
  inset: 0pt,
  clip: true,
)[
  #image(path, width: 100%, height: 100%, fit: "cover")
]

#let member_card(name, initials, profile_path: none) = [
  #grid(
    rows: (44pt, 150pt, auto),
    row-gutter: 0.45em,
    align: center + top,
    block(width: 100%, height: 44pt)[
      #align(center + bottom)[
        #text(size: 15pt, weight: "medium")[#name]
      ]
    ],
    if profile_path == none {
      placeholder_card_body()
    } else {
      profile_card_body(profile_path)
    },
    align(center)[#text(size: 18pt)[#initials]],
  )
]

#let team_entry = [
  #align(center + top)[
    #grid(
      columns: (1fr, 1fr, 1fr, 1fr, 1fr),
      column-gutter: 14pt,
      row-gutter: 0pt,
      align: center + top,
      [#member_card([Florian Beck], [FB])],
      [#member_card([Valentin Bumeder], [VB], profile_path: "../../../figures/team/profile-vb.jpg")],
      [#member_card([Lukas Röß], [LR], profile_path: "../../../figures/team/profile-lr.png")],
      [#member_card([Christopher Kirschner], [CK])],
      [#member_card([Jan Duchscherer], [JD], profile_path: "../../../figures/team/profile-jd.png")],
    )
  ]
]
