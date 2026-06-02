#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP3],
  [CK],
  [MASt3R-SLAM Adapter implementiert; Pipeline-Lauf auf ADVIO funktioniert],
)

#let challenges_table_row = (
  [WP3],
  [CK],
  [Original-`main.py` zerlegen und als Adapter neu bauen],
)

#let next_steps_table_row = (
  [WP3 / WP7],
  [CK],
  [Trajektorie gegen ADVIO-Ground-Truth prüfen, dann Vergleich mit ViSTA-SLAM],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: MASt3R-SLAM Integration])[
    == Adapter-Struktur
    - Neue Klasse `Mast3rSlamBackend` implementiert das bestehende `SlamBackend`-Protokoll parallel zu ViSTA.

    == Laufmodi
    - Offline-Modus: Session läuft im Haupt-Thread der Pipeline und wird frame für frame mit Bildern gefüttert.
    - Streaming-Modus: `MultiprocessSlamSession` spawnt einen Worker-Prozess.
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Challenges])[
    == Original-`main.py` aufbrechen
    - Die `main.py` im MASt3R-SLAM-Repo ist eher ein Script: erwartet
      bestimmte CLI-Argumente, lädt selbst den Datensatz, instanziiert
      Model, Keyframes, Tracker und Backend-Prozess und macht dann
      eine eigene Hauptschleife über alle Frames.
    - Für unsere Pipeline musste das Ganze zerlegt und als eigene
      Klasse nachgebaut werden — also Adapter + `SlamSession` mit
      `step()` / `close()`, damit die Pipeline Frame für Frame reinreichen
      kann.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Next Steps])[
    == Validierung
    - ADVIO-Trajektorie gegen Ground-Truth prüfen
    - SLAM-Updates genauer testen — speziell Verhalten bei
      Loop Closures. Aktuell läuft die Methode durch, aber
      wie plausibel die Ergebnisse wirklich sind, ist noch offen.
    - Ergebnisse anschließend gegen ViSTA-SLAM auf derselben
      Sequenz vergleichen.

    == Performance
    - Aktuell schaffe ich nur ca. 5 FPS — zu wenig für sinnvolles
      Streaming. Muss ich mir genauer anschauen, welche Parameter ich anpassen kann.
  ]
]

#let proposal_detail_body = none
