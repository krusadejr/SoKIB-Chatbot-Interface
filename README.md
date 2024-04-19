# sokib
Projekt mit Stadtverwaltung für KI-Chatbot mit Verbindung mit Geodaten. \
Das Projekt wurde als API entwickelt. Die Fragen von den Benutzern können als HTTP Requests an die API geschickt. Die API verarbeitet die Requests und fragt die relevanten Geo-Informationen wie Naturschutzgebiet usw. über Geo-Daten-APIs ab. Außerdem werden noch relevante Informationen in der Wissensbasis (Vektor-Datenbank) gesucht und zurückgegeben.
Geo-Informationen, zusammen mit Daten aus der Vektor-Datenbank, werden als zusätzliche Informationen an OpenAI APIs übergeben. Am Ende wird eine Antwort basiert auf der eingelieferten Informationen generiert und von der API zurückgegeben.

## 1. Verwendete Tools
[OpenAI API](https://platform.openai.com/docs/api-reference)\
[Pinecone](https://www.pinecone.io)\
[GPT Retrieval Plugin](https://github.com/openai/chatgpt-retrieval-plugin)\
[FastAPI](https://fastapi.tiangolo.com)

## 2. Verbindung mit Geo-Daten
Die Verbindung mit Geo-Daten erfolgt mit WFS (Vektordienst) anhand REST APIs und HTTP Abfragen, um die geografischen Informationen wie Bauleitplanung sowie Naturschutzgebiete abzufragen. Die Flurnummer und Flurstücknummer werden vom Nutzer eingegeben. Der Ablauf der Abfragen ist wie folgt erläutert:\
(1) Hole Flurstück auf Basis der eingegebenen Flur- und Flurstücknummer mithilfe von Filtern, Beispiel (Flur 093, Flurstück 27):
```
https://isk.geobasis-bb.de/ows/alkis_vereinf_wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION=1.1.0&TYPENAME=ave:Flurstueck&SRSNAME=urn:ogc:def:crs:EPSG::25833&FILTER=
<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc" xmlns:ave="http://repository.gdi-de.org/schemas/adv/produkt/alkis-vereinfacht/2.0">
	<ogc:And>
		<ogc:PropertyIsEqualTo>
		    <ogc:PropertyName>ave:gemarkung</ogc:PropertyName>
			<ogc:Literal>Brandenburg</ogc:Literal>
		</ogc:PropertyIsEqualTo>
		<ogc:PropertyIsEqualTo>
			<ogc:PropertyName>ave:flur</ogc:PropertyName>
			<ogc:Literal>093</ogc:Literal>
		</ogc:PropertyIsEqualTo>
		<ogc:PropertyIsEqualTo>
			<ogc:PropertyName>ave:flstnrzae</ogc:PropertyName>
			<ogc:Literal>27</ogc:Literal>
		</ogc:PropertyIsEqualTo>
	</ogc:And>
</ogc:Filter>
```
Aus der Antwort von der obigen Abfrage bekommt man die Polygon-Informationen des Flurstückes. Die Polygon-Informationen bestimmen die feste geografische Position des Flurstückes und werden dann als Inputs für weitere Abfragen genutzt, um wie z.B. die Bauleitplanung zu ermitteln. Die Polygon-Informationen sehen wie folgt aus:
```
<gml:Polygon>
    <gml:exterior>
        <gml:LinearRing>
            <gml:posList>332231.249 5808121.153 332384.023 5807962.764 332383.877 5807976.037 332382.173 5807984.755 332380.271 5807988.915 332376.141 5807991.664 332368.275 5807998.627 332359.982 5808023.401 332249.579 5808137.924 332248.054 5808137.858 332231.249 5808121.153</gml:posList>
        </gml:LinearRing>
    </gml:exterior>
</gml:Polygon>
```

(2) Hole Bauleitplanung des Flurstückes. Dafür wird eine andere API über Bauleitplanung verwendet. Beispiel:
```
https://gdi.stadt-brandenburg.de/ws/bauleitplanung?TYPENAME=ms:Bauluecken_Flaechen&SERVICE=WFS&version=1.1.0&REQUEST=GetFeature&srsName=urn:ogc:def:crs:EPSG::25833&FILTER=
<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc" xmlns:ms="http://mapserver.gis.umn.edu/mapserver" xmlns:gml="http://www.opengis.net/gml">
	<ogc:Intersects>
		<ogc:PropertyName>the_geom</ogc:PropertyName>
		<gml:Polygon>
			<gml:exterior>
				<gml:LinearRing>
					<gml:posList>334402.273 5810230.76 334411.686 5810197.159 334417.013 5810198.55 334458.214 5810219.789 334452.012 5810243.717 334402.273 5810230.76</gml:posList>
				</gml:LinearRing>
			</gml:exterior>
		</gml:Polygon>
	</ogc:Intersects>
</ogc:Filter>
```
Der Filter prüft das Flurstück auf Überschneidungen mit Bauleitplan. Wenn ein Element mit dem Namen "gml:featureMember" zurückgibt, bedeutet es, eine Überschneidung ist zu finden. Der Bau ist dann nur unter bestimmten Bedingungen zulässig.

(3) Hole Informationen über Naturschutzgebiet des Flurstückes mit einer weiteren API. Beispiel:
```
https://inspire.brandenburg.de/services/schutzg_wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION=1.1.0&TYPENAME=app:nsg&SRSNAME=urn:ogc:def:crs:EPSG::25833&FILTER=
<ogc:Filter xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc">
	<ogc:Intersects>
		<ogc:PropertyName>the_geom</ogc:PropertyName>
			<gml:Polygon>
                <gml:exterior>
                    <gml:LinearRing>
                        <gml:posList>332231.249 5808121.153 332384.023 5807962.764 332383.877 5807976.037 332382.173 5807984.755 332380.271 5807988.915 332376.141 5807991.664 332368.275 5807998.627 332359.982 5808023.401 332249.579 5808137.924 332248.054 5808137.858 332231.249 5808121.153</gml:posList>
                    </gml:LinearRing>
                </gml:exterior>
           </gml:Polygon>
	</ogc:Intersects>
</ogc:Filter>
```
Ähnlich wie bei Überprüfung der Bauleitplanung, hier werden die Überschneidungen mit Naturschutzgebiet geprüft. Wenn eine Überschneidung festgelegt ist, dürfen keine Bauaktivitäten stattfinden. 

## 3. Prototyp Einrichten
### Vektordatenbank Pinecone einrichten
Gehe auf https://www.pinecone.io/, erstelle ein Konto und melde sich an. Dann kann man zum Dashboard gehen und auf "Create Index" klicken. Dadurch gelangt man auf die Seite, auf der die erste Vektordatenbank erstellt werden kann (s. Bild).
![Example Pinecone set up](/pic/pinecone.png)

Hier muss man beachten, dass die Nummer bei Dimensions 1536 fest ist. Diese Nummer sollte mit dem Embedding Modell übereinstimmen, d. h. mit der Dimensionen von `text-embedding-ada-002`. Index sollte dann wie folgt aussehen:
![Example Pinecone index](/pic/index.png)

Später müssen noch einige Umgebungsvariablen festgelegt werden. Die Umgebungsvariablen für Pinecone sind `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT` und `PINECONE_INDEX`. `PINECONE_API_KEY` findet man im Dashboard bei "API Keys", `PINECONE_ENVIRONMENT` ist bei Index (wie das Bild oben zeigt) zu sehen, in diesem Beispiel ist "gop-starter", `PINECONE_INDEX` ist der Index-Name "gpt-test". 

### GPT Retrieval Plugin (Datenbank Interface)
Auf der GitHub-Seite sind die Konfigurationsschritte bereits beschrieben. Hier werden die Hauptschritte nochmal dokumentieren.
1 Python 3.10 installiern
2 Klone das Repository `git clone https://github.com/openai/chatgpt-retrieval-plugin.git`
3 Gehe in das geklonte Verzeichnis `cd /path/to/chatgpt-retrieval-plugin`
4 Poetry installieren `pip install poetry`
5 Erstelle eine neue virtuelle Umgebung mit Python 3.10 `poetry env use python3.10`
6 Aktiviere die virtuelle Umgebung `poetry shell`
7 Dependencies installieren `poetry install`
8 Bearer Token erstellen unter https://jwt.io/. Die Werte bei Paylod sind nach beliebigen zu bearbeiten
9 Umgebungsvariablen einrichten wie folgt. Die Texte in <> müssen entsprechend ersetzt werden. `OPENAI_API_KEY` kann man bei https://platform.openai.com/ holen

	export DATASTORE=pinecone
	export OPENAI_API_KEY=<your_openai_api_key>
	export BEARER_TOKEN=<your_database_interface_api_key>
	export PINECONE_API_KEY=<your_pinecone_api_key>
	export PINECONE_ENVIRONMENT=<your_pinecone_region_name>
	export PINECONE_INDEX=<your_index_name>

10 Führe die Datenbank Interface lokal aus `poetry run start`
11 Auf die API-Dokumentation zugreifen unter http://0.0.0.0:8000/docs und Endpoint testen

## 4. Projekt Starten
### Projekt Vorbereiten
1 Klone das Repository `git clone https://github.com/huwenxin/sokib.git`
2 Gehe in das geklonte Verzeichnis `cd /path/to/sokib`
3 Öffne die Datei "secrets.py" und ersetze "xxxxx" mit richtigen Tokens

### Dokumente in Vektordatenbank Speichern
1 Öffne die Datei "database_utils.py"
2 Pfad zu den benötigten Dokumenten, die in der Vektordatenbank gespeichert werden, eingeben (s. Bild)
![Pfad bearbeiten](/pic/Pfad.png)
3 Ausführe `python database_utils.py`

Wenn das Hochladen erfolgreich ist, werden Sie folgende Messages sehen

	file1 uploaded successfully.
	file2 uploaded successfully.
	file3 uploaded successfully.
	file4 uploaded successfully.

### Chat Interface Starten
Öffne die Datei "main.py". \
Für die API Entwicklung wurde [FastAPI](https://fastapi.tiangolo.com) verwendet. Bei mancher Entwicklungsumgebung ist es möglich, die benötigten Pakete per Klick auf Fehlermeldung zu installieren. Wenn das nicht funktioniert, muss man die Pakete manuell installieren: \
1 Ausführe in Terminal: `pip install "fastapi[all]"` \
2 Server Starten: `uvicorn main:app --port 8888 --reload`. Um Konflikte zu vermeiden, wird der Server auf Port 8888 gestartet, weil Datenbank Interface schon Port 8000 besitzt. 

### HTTP Requests
Um Requests zu schicken, wird die Methode `POST` genutzt, da die Informationen über Flur, Flurstück sowie der Text der konkreten Frage auch verschickt werden sollten. In der Datei "main.py" gibt es zwei Pfade: `/chat` und `/chatIBM`.
`chatIBM` ist spezifisch für IBM Watsonx Assistant, um die komplexen Abfragen von IBM Watsonx Assistant zu verarbeiten, denn wir die Funktion anhand dieser Anwendung demonstrieren wollen. `/chat` ist allgemeiner für alle selbstentwickelten Anwendungen geeignet. Request Body und Response sind beide in JSON Format. Das Request Body sollte dann wie folgt aussehen:\
```
{
    "flur": "093",
    "flstnrzae": "27",
    "question": "Ist es erlaubt ein Haus zu bauen bei Flur 093, Flurstück 27?"
}
```
Die zurückgegebene Antwort sollte wie folgt aussehen:
```
{ "message": "some text" }
```
