// DEUTSCHE REFERENZ-FASSUNG (Christopher Kirschner) — render-basierte
// Rekonstruktionstreue (Metrik). Inhaltlich identisch zu
// ck-image-quality-metrics.typ, nur auf Deutsch, zum schnellen Gegenchecken.
// NICHT in main.typ eingebunden (Report ist englisch).

== Render-basierte Rekonstruktionstreue

Diese Metrik bewertet die Rekonstruktion im *Bildraum*: Wie gut sieht die
geschätzte Szene aus, wenn man sie aus den geschätzten Kameraposen betrachtet? Das
ist eine eigene Frage, getrennt vom geometrischen Cloud-zu-Cloud-Vergleich. Der
geometrische Test misst, wie genau die 3D-Form ist; unser Bildtest misst, wie gut
die Wolke Farben und Struktur der Szene wiedergibt und wie viel von jedem Bild sie
füllt. Zusammen ergeben sie ein vollständigeres Bild.

Um die Bildmetriken anzuwenden, muss die Rekonstruktion zuerst zu einem Bild
gerendert werden. Als einfache Basis rendern wir die dichte Punktwolke per
Projektion: Jeder 3D-Punkt wird direkt in die Bildebene geworfen. Die Metriken
selbst hängen aber nicht an dieser Wahl. Man könnte die Punktwolke genauso durch
ein 3D Gaussian Splatting- oder NeRF-Modell ersetzen und dieselben Metriken auf
dessen gerenderte Ansichten anwenden @mildenhall2020nerf @kerbl2023gaussian; nur
der Renderer würde sich ändern. Anschließend vergleichen wir jedes gerenderte Bild
Pixel für Pixel mit dem echten Eingabebild.

Die Projektion im Detail: Für einen Weltpunkt $X$ und
eine Kamerapose mit Rotation $R$ und Translation $t$ ist der Punkt im Kamerasystem
$X_c = R^top (X - t)$, und seine Pixelposition ist $x = K X_c \/ Z_c$. Dabei
enthält $K$ die Brennweiten $f_x, f_y$ und die Bildmitte $(c_x, c_y)$, und $Z_c$
ist die Tiefe des Punkts. Fallen mehrere Punkte auf dasselbe Pixel, gewinnt der
nächste; Pixel ohne Punkt bleiben leer. Wir programmieren diese Projektion nicht
selbst; die Berechnung übernimmt Open3D @zhou2018open3d.

Wir bewerten nur die Pixel, die die Wolke tatsächlich füllt. Diese gefüllten Pixel
bilden eine Menge $Omega$. Wir vergleichen das echte Bild $I$ und das gerenderte
Bild $hat(I)$ nur auf $Omega$, damit die Wolke nicht für Pixel bestraft wird, die
sie nie abgedeckt hat. Dort berechnen wir drei einfache Fehler,
$ "L1" = 1/N sum_(p in Omega) abs(I_p - hat(I)_p), quad
  "MSE" = 1/N sum_(p in Omega) (I_p - hat(I)_p)^2, $
$ "PSNR" = 10 log_10 (L^2 \/ "MSE"), $
wobei $N$ die Anzahl der gefüllten Pixel ist und $L$ der Wertebereich ($L = 255$
für 8-Bit-Bilder). Ein höherer PSNR bedeutet eine bessere Übereinstimmung.
Zusätzlich berechnen wir den Strukturähnlichkeitsindex (SSIM), der misst, wie
ähnlich die lokale Bildstruktur ist; er reicht von $-1$ bis $1$ ($1$ heißt
identisch) @wang2004ssim. Zuletzt geben wir die Coverage an, den Anteil der Pixel,
den die Wolke füllt, da die anderen Werte nur diese Pixel zählen.

Ein Detail zur Maske: Da $Omega$ entscheidet, *welche* Pixel in den Mittelwert
eingehen, funktioniert die Maskierung bei L1 und PSNR sauber, denn diese Werte
werden pixelweise berechnet. SSIM ist anders: Sein Wert entsteht über ein
$7 times 7$-Fenster um jeden Pixel. Liegt ein gefüllter Pixel am Rand eines Lochs,
reicht sein Fenster in die leeren (schwarzen) Bereiche und sein SSIM-Wert sinkt —
obwohl das Pixel selbst gültig ist. Die Maske kann das nicht mehr reparieren, weil
der Loch-Einfluss schon im Wert steckt. Eine dünne, löchrige Wolke trifft den SSIM
deshalb härter als PSNR oder L1.

Insgesamt eignen sich diese Zahlen am besten zum Vergleich von Methoden auf
derselben Sequenz, nicht als absoluter Bildqualitätswert.
