#import "../template.typ": *

#import "_shared/meeting-blocks.typ" as meeting_blocks
#import "_shared/team.typ" as team
#import "_shared/timeline.typ" as timeline_mod
#import "_shared/workpackages.typ" as workpackages

#import "_shared/meeting-01.typ" as meeting_01
#import "_shared/meeting-02.typ" as meeting_02
#import "meeting-02/fb.typ" as m02_fb
#import "meeting-02/vb.typ" as m02_vb
#import "meeting-02/lr.typ" as m02_lr
#import "meeting-02/ck.typ" as m02_ck
#import "meeting-02/jd.typ" as m02_jd
#import "meeting-03/fb.typ" as m03_fb
#import "meeting-03/vb.typ" as m03_vb
#import "meeting-03/lr.typ" as m03_lr
#import "meeting-03/ck.typ" as m03_ck
#import "meeting-03/jd.typ" as m03_jd
#import "meeting-04/fb.typ" as m04_fb
#import "meeting-04/vb.typ" as m04_vb
#import "meeting-04/lr.typ" as m04_lr
#import "meeting-04/ck.typ" as m04_ck
#import "meeting-04/jd.typ" as m04_jd
#import "meeting-05/fb.typ" as m05_fb
#import "meeting-05/vb.typ" as m05_vb
#import "meeting-05/lr.typ" as m05_lr
#import "meeting-05/ck.typ" as m05_ck
#import "meeting-05/jd.typ" as m05_jd

#let deck_title = [#text(
  size: 37pt,
)[Challenge 5 \ Uncalibrated Monocular VSLAM]]
#let extra = [Pattern Recognition & Machine Learning \ Prof. Dr. Friedrich]

#let meeting_items_01 = (
  [Async Kick-Off],
  [Update Meeting 1],
  datetime(year: 2026, month: 4, day: 1),
)
#let meeting_items_02 = (
  [Project Proposal],
  [Update Meeting 2],
  datetime(year: 2026, month: 4, day: 15),
)
#let meeting_items_03 = (
  [Status Quo],
  [Update Meeting 3],
  datetime(year: 2026, month: 4, day: 29),
)
#let meeting_items_04 = (
  [Status Quo],
  [Update Meeting 4],
  datetime(year: 2026, month: 5, day: 22),
)
#let meeting_items_05 = (
  [Status Quo],
  [Update Meeting 5],
  datetime(year: 2026, month: 6, day: 12),
)

#let display_meeting_date(date) = date.display(
  "[day padding:none]. [month repr:short] [year]",
)

#let meeting_subtitle(items) = [
  #items.at(1) \
  #display_meeting_date(items.at(2))
]

#let member_modules(fb, vb, lr, ck, jd) = (
  (name: [Florian Beck], module: fb),
  (name: [Valentin Bumeder], module: vb),
  (name: [Lukas Röß], module: lr),
  (name: [Christopher Kirschner], module: ck),
  (name: [Jan Duchscherer], module: jd),
)

#let meeting_02_members = member_modules(m02_fb, m02_vb, m02_lr, m02_ck, m02_jd)
#let meeting_03_members = member_modules(m03_fb, m03_vb, m03_lr, m03_ck, m03_jd)
#let meeting_04_members = member_modules(m04_fb, m04_vb, m04_lr, m04_ck, m04_jd)
#let meeting_05_members = member_modules(m05_fb, m05_vb, m05_lr, m05_ck, m05_jd)

#let status_meetings = (
  (items: meeting_items_03, members: meeting_03_members),
  (items: meeting_items_04, members: meeting_04_members),
  (items: meeting_items_05, members: meeting_05_members),
)

#let meeting_footer(items) = project_footer(
  footer_authors: team.team_members_footer,
  footer_label: [Update Meetings],
  footer_date: [#display_meeting_date(items.at(2))],
)

#let meeting_slide(items, title: [], body) = slide(
  title: title,
  footer: meeting_footer(items),
)[#body]

#let meeting_status_table_slide(
  items,
  title: [],
  rows: (),
) = meeting_blocks.status_table_slide(
  title: title,
  rows: rows,
  footer: meeting_footer(items),
)

#let collect_rows(members, pick) = members.map(member => pick(member.module))

#let collect_detail_bodies(items, members, pick) = (
  members
    .filter(
      member => pick(member.module) != none,
    )
    .map(member => pick(member.module)(items))
)

#let status_rows(members, pick) = (
  ..collect_rows(members, pick),
  ..meeting_blocks.placeholder_status_rows,
)

#let status_sections = (
  (
    table_title: [What was done?],
    row_picker: module => module.done_table_row,
    detail_picker: module => module.done_detail_body,
  ),
  (
    table_title: [What were the challenges?],
    row_picker: module => module.challenges_table_row,
    detail_picker: module => module.challenges_detail_body,
  ),
  (
    table_title: [What are the next steps?],
    row_picker: module => module.next_steps_table_row,
    detail_picker: module => module.next_steps_detail_body,
  ),
)

#let render_status_meeting(items, members) = [
  #section-slide(title: items.at(0), subtitle: meeting_subtitle(items))
  #for section in status_sections [
    #meeting_status_table_slide(
      items,
      title: section.table_title,
      rows: status_rows(members, section.row_picker),
    )
    #for detail_body in collect_detail_bodies(
      items,
      members,
      section.detail_picker,
    ) [
      #detail_body
    ]
  ]
]

#project_deck(
  title: deck_title,
  subtitle: [Update Meetings],
  authors: team.team_members_inline,
  footer_authors: team.team_members_footer,
  extra: extra,
  footer_label: [Update Meetings],
  footer_date: [#display_meeting_date(meeting_items_01.at(2))],
)[
  #title-slide()

  #meeting_slide(meeting_items_01, title: [Team])[
    #align(center + horizon)[
      #team.team_entry
    ]
  ]

  #section-slide(
    title: meeting_items_01.at(0),
    subtitle: meeting_subtitle(meeting_items_01),
  )

  #meeting_slide(meeting_items_01, title: [Team Leader])[
    #team.leader_note
  ]

  #meeting_slide(meeting_items_01, title: [Team Charter])[
    #meeting_01.team_charter
  ]

  #meeting_slide(meeting_items_01, title: [Challenge Clarifications])[
    #meeting_01.challenge_clarifications
  ]

  #meeting_slide(meeting_items_01, title: [Goals])[
    #meeting_01.goals
  ]

  #meeting_slide(meeting_items_01, title: [Non-Goals])[
    #meeting_01.non_goals
  ]

  #section-slide(
    title: meeting_items_02.at(0),
    subtitle: meeting_subtitle(meeting_items_02),
  )

  #meeting_slide(meeting_items_02, title: [Goals (refined)])[
    #meeting_02.goals_refined
  ]

  #meeting_slide(meeting_items_02, title: [Non-Goals (refined)])[
    #meeting_02.non_goals_refined
  ]

  #meeting_slide(meeting_items_02, title: [Work Packages & Responsibilities])[
    #workpackages.work_packages_table()
  ]

  #meeting_slide(meeting_items_02, title: [References])[
    #if meeting_02.reference_links != none [
      #v(0.85em)
      #color-block(title: [Reference Links])[
        #meeting_02.reference_links
      ]
    ]
  ]

  #meeting_slide(meeting_items_02, title: [Timeline (rough)])[
    #timeline_mod.timeline
  ]

  #for detail_body in collect_detail_bodies(
    meeting_items_02,
    meeting_02_members,
    module => module.proposal_detail_body,
  ) [
    #detail_body
  ]

  #for meeting in status_meetings [
    #render_status_meeting(meeting.items, meeting.members)
  ]
]
