// DEUTSCHE REFERENZ-FASSUNG (Christopher Kirschner) — MASt3R-SLAM-Integration.
// Inhaltlich identisch zu ck-mast3r-integration.typ, nur auf Deutsch, zum
// schnellen Gegenchecken. NICHT in main.typ eingebunden (Report ist englisch).

== MASt3R-SLAM-Integration

MASt3R-SLAM ist die zweite Methode, die wir in den Benchmark aufnehmen. Sie ist
ein lernbasiertes SLAM-Verfahren, das aus einer einzelnen Kamera eine dichte
3D-Rekonstruktion erstellt @murai2025mast3rslam. Sie schätzt die 3D-Szene direkt
aus den Bildern und braucht dafür keine Kamerakalibrierung. Deshalb eignet sie
sich für unkalibrierte Aufnahmen wie zum Beispiel ein Smartphone-Video.

Drei Dinge unterscheiden MASt3R von einem klassischen SLAM-System. Erstens steckt
ein großes, vortrainiertes Netz dahinter (ein Foundation Model): Es hat 3D-Geometrie
aus sehr vielen Bildern gelernt und liefert deshalb auch bei ungewohnten Aufnahmen
robuste 3D-Schätzungen.

Zweitens braucht MASt3R die Kameraparameter nicht im Voraus, vor allem nicht die
Brennweite. Ein klassisches Verfahren benötigt die Brennweite, um aus einem Pixel
einen Sehstrahl in die Szene zu legen, und bestimmt die Tiefe erst danach. MASt3R
dreht das um: Das Netz sagt für jedes Pixel direkt den 3D-Punkt voraus — also
Richtung und Tiefe zugleich. Die Brennweite muss man nicht kennen; sie lässt
sich aus diesen 3D-Punkten nachträglich ablesen. Auch die Zuordnung zwischen
zwei Bildern läuft so direkt im 3D-Raum und nicht über klassische 2D-Bildmerkmale.

Drittens darf sich die Kamera während der Aufnahme ändern — etwa ein Zoom mitten im
Video. Das ist möglich, weil die Brennweite nicht fest vorgegeben ist.

Wir binden MASt3R-SLAM über dieselbe Schnittstelle ein wie ViSTA-SLAM. Beide
Methoden lesen dieselben Eingabebilder und schreiben dieselben Ausgabedateien.

MASt3R-SLAM läuft mit oder ohne bekannte Kalibrierung. Ist die Kalibrierung
vorhanden, geben wir sie der Methode mit. Fehlt sie, schätzt die Methode die
Brennweite der Kamera selbst. In beiden Fällen läuft sie auf dem rohen Video.

Eine zweite Einstellung steuert, wie dicht die Rekonstruktion wird. Sie legt fest,
wie oft ein neuer Keyframe hinzukommt. Mehr Keyframes ergeben eine dichtere
Punktwolke und decken mehr vom Bild ab, der Lauf dauert dann aber länger.

Jeder Lauf erzeugt zwei Dateien: den Kamerapfad im TUM-Format und eine dichte,
eingefärbte Punktwolke. Beide Dateien sind die Eingabe für die Trajektorien- und
Rekonstruktions-Evaluation in den nächsten Abschnitten.
