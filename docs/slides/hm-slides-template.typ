#import "@preview/definitely-not-isec-slides:1.0.1": *
#import "@preview/tableau-icons:0.331.0": *
#import "@preview/muchpdf:0.1.1": muchpdf
#import "@preview/booktabs:0.0.4": *
#import "@preview/codly:1.3.0": *
#import "@preview/tdtr:0.5.0": *

#let theme_color_primary_hm = rgb("fc5555")
#let theme_color_block = rgb("f4f6fb")
#let theme_color_footer = rgb("808080")

// ---------------------------------------------------------------------------
// Note helpers
// ---------------------------------------------------------------------------

#let note_inset = 1em
#let note_border_radius = 0.5em

#let note_info_border_color = black
#let note_info_background_color = gray.lighten(80%)
#let note_warning_border_color = red
#let note_warning_background_color = orange.lighten(80%)
#let note_good_border_color = green
#let note_good_background_color = lime.lighten(80%)

#let note-box(
  content,
  width: auto,
  background: note_info_background_color,
  border: note_info_border_color,
  bold: true,
) = {
  let weight = "light"
  if bold {
    weight = "semibold"
  }

  block(
    stroke: 1pt + border,
    fill: background,
    inset: note_inset,
    radius: note_border_radius,
    width: width,
  )[
    #set text(fill: black, weight: weight)
    #content
  ]
}

#let note(content, width: auto, background: note_info_background_color, border: note_info_border_color, bold: true) = {
  note-box(content, width: width, background: background, border: border, bold: bold)
}

#let warning-note(content, width: auto) = {
  note-box(
    content,
    width: width,
    background: note_warning_background_color,
    border: note_warning_border_color,
    bold: true,
  )
}

#let good-note(content, width: auto) = {
  note-box(
    content,
    width: width,
    background: note_good_background_color,
    border: note_good_border_color,
    bold: true,
  )
}

#let todo() = {
  set text(black)
  text(size: 120pt)[#emoji.chicken.baby #text(fill: gradient.linear(..color.map.rainbow))[TUDÜ]]
}

// ---------------------------------------------------------------------------
// Code blocks (minimal raw styling)
// ---------------------------------------------------------------------------

/// Render a minimal code block (raw) for slides.
#let code-block(
  body,
  size: 13pt,
  fill: theme_color_block,
  stroke: 0.75pt + theme_color_block.darken(12%),
  radius: 8pt,
  inset: (x: 0.6em, y: 0.45em),
) = [
  #show raw.where(block: true): set text(font: "DejaVu Sans Mono", size: size)
  #show raw.where(block: true): block.with(
    fill: fill,
    stroke: stroke,
    radius: radius,
    inset: inset,
  )
  #body
]

/// Code block wrapped as a captioned figure (for slides).
#let code-figure(
  caption: none,
  size: 13pt,
  body,
) = figure(
  caption: caption,
  code-block(size: size)[body],
)

// Redefine the slide function to use custom logo in header (no institute name)
#let slide(
  title: auto,
  footer: auto,
  alignment: none,
  outlined: true,
  ..args,
) = touying-slide-wrapper(self => {
  let info = if footer == auto {
    self.info + args.named()
  } else {
    self.info + args.named() + (footer: footer,)
  }

  // Custom Header with logo only (no institute name)
  let header(self) = {
    let hdr = if title != auto { title } else { self.store.header }
    show heading: set text(size: 24pt, weight: "semibold")

    grid(
      columns: (self.page.margin.left, 1fr, auto, 0.5cm),
      block(), heading(level: 1, outlined: outlined, hdr), move(dy: -0.31cm, self.store.logo), block(),
    )
  }

  // Footer with page numbers and date
  let footer(self) = context {
    set block(height: 100%, width: 100%)
    set text(size: 15pt, fill: self.colors.footer)

    grid(
      columns: (self.page.margin.bottom - 1.68%, 1.3%, auto, 1cm),
      block(fill: self.colors.primary)[
        #set align(center + horizon)
        #set text(fill: white, size: 14pt)
        #utils.slide-counter.display()
      ],
      block(),
      block[
        #set align(left + horizon)
        #set text(size: 14pt)
        #info.at("footer", default: "")
      ],
      block(),
    )

    if self.store.progress-bar {
      place(bottom + left, float: true, move(dy: 1.05cm, components.progress-bar(
        height: 3pt,
        self.colors.primary,
        white,
      )))
    }
  }

  let self = utils.merge-dicts(self, config-page(
    header: header,
    footer: footer,
  ))

  set align(
    if alignment == none {
      self.store.default-alignment
    } else {
      alignment
    },
  )

  touying-slide(self: self, ..args)
})

// Default figure caption (title) styling for slides.
#show figure.caption: set text(size: 14pt)

// Override color-block to have rounded corners
#let color-block(
  title: [],
  icon: none,
  spacing: 0.78em,
  color: none,
  color-body: none,
  body,
) = [
  #touying-fn-wrapper((self: none) => [
    #show emph: it => {
      text(weight: "medium", fill: self.colors.primary, it.body)
    }

    #showybox(
      title-style: (
        color: white,
        sep-thickness: 0pt,
      ),
      frame: (
        radius: 8pt, // Rounded corners!
        thickness: 0pt,
        border-color: if color == none { self.colors.primary } else { color },
        title-color: if color == none { self.colors.primary } else { color },
        body-color: if color-body == none { self.colors.lite } else { color-body },
        inset: (x: 0.55em, y: 0.65em),
      ),
      above: spacing,
      below: spacing,
      title: if icon == none {
        align(horizon)[#strong(title)]
      } else {
        align(horizon)[
          #draw-icon(icon, height: 1.2em, baseline: 20%, fill: white) #h(0.2cm) #strong[#title]
        ]
      },
      body,
    )
  ])
]

#let io-formulation(input-items, output-items) = [
  #grid(
    gutter: 0.4cm,
    color-block(title: [Input], color-body: rgb("#d5e8d4"))[
      #input-items
    ],
    color-block(title: [Output], color-body: rgb("#f8cecc"))[
      #output-items
    ],
  )
]
