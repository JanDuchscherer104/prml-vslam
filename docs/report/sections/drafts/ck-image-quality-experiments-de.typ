// DEUTSCHE REFERENZ-FASSUNG (Christopher Kirschner) — Bildqualitäts-Benchmark &
// Werkzeuge (Experimente). Inhaltlich identisch zu
// ck-image-quality-experiments.typ, nur auf Deutsch, zum schnellen
// Gegenchecken. NICHT in main.typ eingebunden (Report ist englisch).

== Bildqualitäts-Benchmark und Werkzeuge

Wir führen diese Evaluation als eigene Pipeline-Stufe aus. Für einen fertigen Lauf
lädt die Stufe die Punktwolke, den Kamerapfad und die Kameradaten. Sie rendert ein
Bild pro Kamerapose und paart es mit dem zeitlich nächsten Eingabebild. Dann
bewertet sie jedes Paar und speichert die Zahlen, zusammen mit einigen
Beispielbildern. Weil alles per Skript läuft und auf der Festplatte landet, lässt
sich die Evaluation jederzeit wiederholen.

Zusätzlich haben wir der App eine Seite hinzugefügt, um die Ergebnisse anzusehen.
Dort kann man einen Lauf auswählen, die wichtigsten Werte sehen (PSNR, SSIM,
Coverage), den Werten Bild für Bild folgen, die Beispielbilder nebeneinander
durchblättern und mehrere Methoden in einer Tabelle vergleichen.

@tbl-image-de zeigt die Ergebnisse auf der ADVIO-Sequenz advio-15 @cortes2018advio.
ViSTA-SLAM bewertet 357 Bildpaare und füllt im Schnitt 79% jedes Bildes,
MASt3R-SLAM 154 Paare bei 63% Coverage. In der reinen Bildqualität liegen beide
nah beieinander: PSNR 10.8 gegenüber 11.2 dB und L1 0.19 gegenüber 0.18. Der
deutlichste Unterschied ist die Coverage: ViSTA-SLAM setzt mehr Keyframes, baut so
eine dichtere Wolke und füllt mehr von jedem Bild.

#figure(
  table(
    columns: 6,
    align: (left, center, center, center, center, center),
    table.header(
      [Methode], [Paare], [Coverage], [PSNR (dB)], [SSIM], [L1],
    ),
    [ViSTA-SLAM], [357], [0.79], [10.8], [0.10], [0.19],
    [MASt3R-SLAM], [154], [0.63], [11.2], [0.07], [0.18],
  ),
  caption: [
    Render-basierte Bildqualitäts-Ergebnisse auf ADVIO advio-15. PSNR, SSIM und L1
    sind Mittelwerte über die gefüllten Pixel aller bewerteten Paare; Coverage ist
    der mittlere Anteil gefüllter Pixel.
  ],
) <tbl-image-de>

@fig-sbs-de zeigt ein Beispiel. Das gerenderte Bild (rechts) gibt die wichtigsten
Formen und Farben der Szene wieder, hat aber Löcher dort, wo die Wolke dünn ist.
Genau diese Löcher schlagen sich in der Coverage nieder.

#figure(
  image("../../../figures/render_eval/vista_advio15_sbs_a.png", width: 100%),
  caption: [
    Side-by-Side-Beispiel aus dem ViSTA-SLAM-Lauf auf ADVIO advio-15:
    Eingabe-Frame (links) und die aus derselben geschätzten Pose gerenderte dichte
    Punktwolke (rechts). Das Rendering ist halbdicht und lässt Löcher dort, wo die
    Wolke dünn ist.
  ],
) <fig-sbs-de>

Insgesamt sind diese Zahlen als Vergleich zwischen Methoden auf derselben Sequenz
gedacht, nicht als absoluter Bildqualitätswert. Auf advio-15 liefern MASt3R-SLAM
und ViSTA-SLAM eine ähnliche Rekonstruktionsqualität — PSNR und L1 liegen dicht
beieinander. Der klarste Unterschied ist die Coverage: ViSTA-SLAM setzt mehr
Keyframes, während MASt3R-SLAM in der Standard-Einstellung einen neuen Keyframe
erst hinzunimmt, wenn genug neuer Bildinhalt dazukommt — es erzeugt deshalb weniger
Keyframes und eine etwas dünnere Wolke. Beim SSIM ist zusätzlich Vorsicht geboten:
Er reagiert empfindlich auf die geschätzten Intrinsics — weicht die Brennweite ab,
wirkt das wie ein Zoom und verschiebt die Bildstruktur — und über sein Fenster
zählt er die Löcher indirekt mit (siehe Metrik-Abschnitt). Zusammen mit der
Coverage zeigen die Werte so, wie gut und wie vollständig eine Methode die Szene
rekonstruiert. Seine eigentlichen Stärken spielt MASt3R-SLAM aber dort aus, wo es
schwierig wird: bei einem Zoom während des Videos oder in texturarmen Szenen — etwa
vor einer kahlen, einfarbigen Wand, wo klassische Verfahren kaum Bildmerkmale zum
Verfolgen finden, MASt3R die Geometrie dank seines vortrainierten Netzes aber
trotzdem schätzt.