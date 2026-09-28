# Macro Dashboard — Finland v2.2

**Aamulukemiset.** Yö on ajettu: kuusi vaihetta (W1–W6) haarassa `v2.2-ui`, jokainen omana
committinaan, portti vihreänä. **Mitään ei ole vielä julkaistu** — `main` ja tagi `v2.1` ovat
ennallaan, eikä yksikään vaihe ole pushannut, mergennyt tai tagittanut.

Tässä versiossa **ei muutettu yhtäkään lähdettä, lukua tai hakuskriptiä**. Kyse on käyttöliittymästä.
Siellä missä luku muuttui ruudulla, se johtuu siitä että sivu luki sille väärää aluetasoa (Testikohde)
tai muotoili sen väärin (vuosiluvut, yksiköt).

Katso ensin nämä viisi. Paikallisesti `make serve` (→ `http://localhost:8080/`), julkaisun jälkeen
`https://real-estate-war-lord.github.io/am-dashboard-fi/`. Alla olevat linkit ovat julkaistun sivun
osoitteita; paikallisesti korvaa alkuosa `http://localhost:8080/`-osoitteella.

---

## 1. Testikohteen ensinäyttö — ja oikea aluetaso

<https://real-estate-war-lord.github.io/am-dashboard-fi/#property?p=60.2448,24.8665>

Tutkimusrivi alkaa 1440 × 900 -ruudulla **265 pikselin** kohdalta; ennen se alkoi 496:sta. Nimi,
aluetunnisteet ja viisi toimintopainiketta ovat samalla rivillä, ruudut heti niiden alla, ja
selitysvirke on **ⓘ** tunnisteiden vieressä.

Tärkeämpi muutos on ruuduissa itsessään. Aiemmin pistekohde putosi omasta osa-alueestaan suoraan
kuntaan; nyt ketju on **osa-alue → postinumero → kunta**. Tällä pinnillä:

- **Hinta** oli Helsingin 5 090 €/m² merkinnällä "municipality figure" → nyt **2 280 €/m²**,
  00410 Malminkartanon oma luku, merkinnällä "postal-code figure".
- **Työttömyys** oli Helsingin 12,1 % → nyt **15,2 %**, 00410:n oma.
- **Vuokra ja rikollisuus ovat edelleen kuntalukuja — ja se on oikea vastaus.** 00410:lle on
  olemassa `rent_pno`-luku 18,4, mutta se on *eri indikaattori*: Tilastokeskus lopetti
  postinumerotason vuokrataulun 2025Q4:ään, eikä sitä sekoiteta elävään kuntatason vuokraan.
  Rikollisuus julkaistaan koko maassa vain kunnittain. Mitään ei ole liimattu yhteen, jotta ruutu
  näyttäisi tarkemmalta kuin se on.

## 2. Esitystila

<https://real-estate-war-lord.github.io/am-dashboard-fi/#map?present=1>

Sivupalkki, työkalurivit ja sirurivit pois, isot luvut neljänneksen suuremmiksi, karttojen selitteet
auki, ja yksi lähderivi kiinni ruudun alalaitaan. Käyttöohje kokouksessa on alempana.

## 3. Kartta, joka täyttää ikkunan — ja kertoo mitä siinä on piirretty

<https://real-estate-war-lord.github.io/am-dashboard-fi/#map>

Kartan korkeus **mitataan** kartan omasta yläreunasta ikkunan alareunaan (minimi 560 px) eikä arvata
CSS:llä; Suomi rajataan kuntapolygoneihin eikä käsin kirjoitettuun laatikkoon. Kartan yläpuolinen
rivi kertoo nyt **mikä taso on piirretty** ("municipalities drawn · zoom in for postal codes"), ei
indikaattorin julkaisutasoa — se luki ennen "postal-code level" kuntakartan päällä.

## 4. Data › Areas: `Columns ▾` ja omat sirut

<https://real-estate-war-lord.github.io/am-dashboard-fi/#data/areas/kunta?cols=Market,Taxes>

Taulukko on 40+ saraketta leveä. `Columns ▾` valitsee **indikaattoriryhmiä**, ja valinta on linkissä
(`cols=Market,Taxes`) — ilman avainta taulukko on täsmälleen entisensä, joten vanhat linkit toimivat.
Lajittelusaraketta ei voi piilottaa, ja **CSV sisältää aina kaikki sarakkeet**: piilotus on lukuapu,
ei väite siitä ettei lukua ole.

Sirurivin **`+`** kiinnittää sen indikaattorin joka on näkyvissä, **`×`** irrottaa. Ensimmäisestä
kiinnityksestä lähtien rivi on sinun, enintään 12 kpl. Ne ovat tämän selaimen tietoja
(`localStorage`), **eivät koskaan linkissä** — lähetetty linkki ei saa vaihtaa vastaanottajan
työkaluja.

Näppäimet: **`?`** näyttää listan. `/` hakukenttään, `g m` / `g d` / `g c` / `g p` näkymiin,
`[` ja `]` siirtävät sirurivillä, `P` esitystilaan, `Esc` pois.

## 5. Kuvaajat: yksi asteikko koko buildille — ja tulvakuvaaja, joka näyttää molemmat toistuvuudet

<https://real-estate-war-lord.github.io/am-dashboard-fi/#charts?ind=flood_sea_100&a=kunta:091,kunta:049>
· <https://real-estate-war-lord.github.io/am-dashboard-fi/#area/kunta/091?show=sub>

Pykälät ovat 1 / 2 / 2,5 / 5 × 10ⁿ, **nolla on aina apuviivalla** kun asteikko ylittää sen, ja
asteikko luetaan niistä vuosista jotka kaikki piirretyt sarjat kattavat — yhden sarjan vanha piikki
ei enää litistä muita. Asteikon ulkopuolelle jäävä arvo piirretään reunaan ▲/▼-merkillä, oikea luku
säilyy vihjeessä, ja poisjätetyt vuodet sanotaan kuvaajan alla (myös ladatussa PNG:ssä).

Ilmastokuvaaja piirtää nyt **molemmat toistuvuudet** (1/100a ja 1/1000a) jokaiselle alueelle, pari
kerrallaan ja harvinaisempi vaaleampana saman alueen värinä. Mediaaniviiva on tuolloin pois päältä,
ja alarivi kertoo miksi: yksi katkoviiva kahta eri mittausta kantavalla akselilla voisi kuulua vain
toiselle niistä.

Toinen linkki avaa Helsingin **osa-aluetaulukon**, jossa jokaisella rivillä on kymmenen viime vuoden
sparkline — jokainen rivi omalla asteikollaan (otsikko sanoo sen), ja vuosi jota julkaisija ei ole
julkaissut **katkaisee viivan** sen sijaan että se siltattaisiin.

---

## Esitystila kokouksessa — kolme askelta

1. **Avaa se näkymä jonka haluat näyttää** ja paina **`P`** (tai `▶ Present` oikeassa yläkulmassa).
   Toimii kartalla, aluesivulla, Testikohteessa ja Kuvaajissa. Sivupalkki ja työkalurivit katoavat,
   indikaattori, jakso ja aluepolku tiivistyvät yhdeksi riviksi ylös, luvut kasvavat neljänneksen ja
   alareunaan kiinnittyy lähderivi (julkaisijat · tilanne · sivun osoite) — eli ruudusta otettu kuva
   kantaa itse oman lähdeviitteensä.
2. **Näytä.** Kartan zoomaus ja rajaus eivät muutu esitystilaan mentäessä — kuva ei karkaa kesken
   lauseen. Karttojen selitteet ovat valmiiksi auki, eli et joudu klikkaamaan `Legend ▾` auki
   yleisön edessä. Mikään luku, osio tai huomautus ei katoa: piiloon menevät vain säätimet.
3. **Poistu `Esc`illä** — tai paina `P` uudelleen. Jos haluat lähettää saman näkymän eteenpäin,
   kopioi osoiterivi: `present=1` on linkissä, joten vastaanottaja avaa täsmälleen saman kuvan.

Kaksi lisäkeinoa samaan: **`Ctrl/⌘-P`** tulostaa saman näkymän A4-vaakana (yksi näkymä per sivu,
selitteet auki, säätimet pois), ja tutkimusrivin **`⤓ PNG`** (aluesivu ja Testikohde) lataa
kuvaajan + minikartan yhtenä 3 200 × 1 016 kuvana otsikoineen ja lähderiveineen — valmis diaan.
Huom: jos taustakartan ruudut eivät ole luettavissa (OpenStreetMapin palvelin ei salli sitä),
kuvaan piirretään vain rajat ja alue-etiketit ja alarivi sanoo **· basemap omitted**.

---

## Mitä jäi tekemättä ja miksi

Koko lista perusteluineen on **`docs/v2_2/QA.md`**; mikään niistä ei estä julkaisua. Tärkeimmät:

- **Tutkimusrivin kuvaaja on puhelimessa 80 px korkea eikä sen asteikkoa voi lukea.** Kuvaaja on
  900 × 240 SVG, joka skaalautuu kortin leveyteen; 390 px:ssä tekstistä tulee 3,7 px. Viivat,
  sarjaselite ja kaikki luvut ovat kuvaajan ympärillä tekstinä, joten mitään ei katoa — mutta
  asteikkoa ei lue. Sama koskee Kuvaajat-näkymää puhelimessa; siellä kuvaajan alla oleva
  **Data**-taulukko listaa joka vuoden ja arvon tekstinä. Rehellinen korjaus on **oma geometria alle 1025 px:lle** (vähemmän pykäliä,
  korkeampi laatikko), ja se on ominaisuus, ei QA-korjaus. Venyttäminen olisi kuvaaja, jonka
  kulmakertoimet valehtelevat — se on suljettu pois jo W4:ssä.
- **Kartan selite voi jäädä taitteen alle 1440 × 900 -ruudulla kun pinnikortti on auki.** Kartalla on
  560 px:n lattia; 440 px korkea kartta ei ole Suomen kartta. Tietoinen valinta.
- **Esitystila ei rajaa karttaa uudelleen.** Sivupalkin poistuminen antaa kartalle ~250 px lisää
  leveyttä, mutta keskipiste ja zoom pysyvät: sovellus ei siirrä katsojan näkymää kesken lauseen.
- **`label_short` on katkaistu 28 merkkiin sanan keskeltä jo hakuvaiheessa**
  (`Maantie 11746 Kilpilahden lä`). W6 merkitsee katkaisun kolmella pisteellä, ja koko nimi on
  klikkauksen päässä, mutta itse katkaisu on hakuskriptissä jota tämä haara ei saa muuttaa.
- **Koulujen aluekohtainen keskiarvo (`school_grade_avg`, `schools_n`) ei piirry**, koska mikään
  build ei kirjoita niitä. Putkiston aukko, ei käyttöliittymän.
- **`Columns ▾` on vain Data › Areas -taulukossa** ja sparkline-sarake vain osa-aluetaulukossa;
  molemmat laajenisivat samalla logiikalla muihin taulukoihin.
- **Kiinnitetyt sirut eivät kerro, jos joku niistä ei julkaista tällä tasolla** — rivi voi olla
  lyhyempi kuin muistiin tallennettu lista, sanomatta sitä.

**Budjetit** ovat kireät ja se kannattaa tietää ennen seuraavaa versiota: `dist/index.html`
3 285 650 B / 3 300 000 B (**14 kB jäljellä**), `src/style.css` 165 118 / 168 960 (3,8 kB),
`src/app.js` 463 573 / 471 040 (7,3 kB). Yhtään dataa ei lisätty — kasvu on lähdekoodia. Seuraava
rehellinen askel on riisua kommentit *upotetusta* kopiosta samalla kun repo säilyttää ne, ei poistaa
niitä lähteestä: niissä on kirjattuna neljän julkaisun päätökset.

---

## Julkaisu

Kun olet katsonut yllä olevat viisi ja QA.md:n:

```bash
./overnight.sh release
```

Se tekee: haara `v2.2-ui` puhtaana → portti `gate W6` vielä kerran → `main` päivitetään
GitHubista → `v2.2-ui` mergetään `main`iin (`--no-ff`) → tagi **`v2.2`** → push. GitHub Pages
julkaisee muutaman minuutin kuluessa osoitteeseen
<https://real-estate-war-lord.github.io/am-dashboard-fi/>. Komento **ei julkaise mitään, jos portti
ei ole vihreä** tai jos työhakemisto ei ole puhdas, ja mergekonfliktissa se peruu mergen ja palaa
haaralle.

Yöajon yhteenveto: `./overnight.sh status`. Lokit: `logs/overnight-<päivä>/`. Kuvakaappaukset:
`docs/ui_v2/` (1440 ja 390, mukana `present_*`). Vaihekohtainen kirjanpito:
`docs/v2_2/PROGRESS.md`, päätökset `docs/v2_2/DECISIONS.md`.
