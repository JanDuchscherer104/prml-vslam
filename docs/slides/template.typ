#import "hm-slides-template.typ": *

#let project_footer(
  footer_authors: [],
  footer_label: [],
  footer_date: [],
) = [
  #grid(
    columns: (1fr, auto, 1fr),
    align: bottom,
    align(left)[#text(size: 9pt)[#footer_authors]],
    align(center)[#footer_label],
    align(right)[#footer_date],
  )
]

#let project_deck(
  title: [],
  subtitle: [],
  authors: [],
  footer_authors: none,
  extra: [],
  footer_label: [],
  footer_date: auto,
  body,
) = {
  let footer_authors = if footer_authors == none { authors } else { footer_authors }
  let footer_date = if footer_date == auto {
    [#datetime.today().display("[day padding:none]. [month repr:short] [year]")]
  } else {
    footer_date
  }

  show: definitely-not-isec-theme.with(
    aspect-ratio: "16-9",
    slide-alignment: top,
    progress-bar: true,
    institute: [Munich University of Applied Sciences],
    logo: [#image("../figures/hm-logo.svg", width: 2cm)],
    config-info(
      title: title,
      subtitle: subtitle,
      authors: authors,
      extra: extra,
      footer: [#project_footer(
        footer_authors: footer_authors,
        footer_label: footer_label,
        footer_date: footer_date,
      )],
      download-qr: "",
    ),
    config-common(handout: false),
    config-colors(
      primary: theme_color_primary_hm,
      lite: theme_color_block,
    ),
  )

  set text(size: 17pt, font: "Open Sans")
  show figure.caption: set text(size: 12pt, weight: "medium", fill: theme_color_footer.darken(40%))
  show link: set text(fill: blue)
  show link: it => underline(it)

  body
}
