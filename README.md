# Easee Smart Charging

Slim laden, Equalizer-inzicht, laadkosten en een app-achtige dashboardkaart voor je Easee-laadpaal in Home Assistant — gebouwd bovenop de bestaande Easee-integratie. Geen tweede login, geen extra belasting van de Easee-cloud.

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=George-120&repository=ha-easee-smart&category=integration)
[![Integratie toevoegen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=easee_smart)

![Easee Smart-kaart](docs/preview.png)

*English and Deutsch below.*

## Wat het doet

- **Kies gewoon je laadpaal.** De integratie vindt je Easee-laadpalen en Equalizer zelf en herkent het model (Home, Charge, Charge Lite, Max, Up, Core, Pro, One).
- **Slim laden op dynamische prijzen.** De day-ahead beursprijzen (EPEX SPOT, voorheen APX) worden automatisch per kwartier opgehaald voor vandaag en morgen, voor elke Europese prijszone — zonder account of extra integratie. Vul de opslag van je contract in, dan rekent hij met (beurs + opslag + energiebelasting) × (1 + btw). Je stelt een vertrektijd en hoeveel je wilt laden in (kWh, of accupercentage als je auto een accusensor heeft) en de integratie kiest de goedkoopste kwartieren.
- **Laden op zonne-overschot.** Met een Easee Equalizer gebruikt de integratie automatisch de gemeten afname en teruglevering. Zonder Equalizer voeg je je **hoofdaansluiting** toe: je slimme meter (P1) wordt automatisch herkend — HomeWizard P1 heeft voorrang omdat die het nauwkeurigst is, daarna DSMR, P1 Monitor, Zonneplan Connect, Tibber en Enphase, en je kiest je hoofdzekering (bijv. 3×25 A). Achteraf wijzigen kan altijd via *Configureren → Hoofdaansluiting*. Start- en stopvertraging voorkomen pendelen.
- **Zon + slim.** Laadt overdag van de zon en vult het tekort aan in de goedkoopste uren vóór vertrek.
- **Auto's koppelen — elk merk.** Tot zes auto's. Kies het apparaat van je auto (Kia, Hyundai, Tesla, VW, BMW, Polestar, …) en Easee Smart Charging vult automatisch het accuniveau, de stekker-sensor, de laadlimiet, de actieradius en de knoppen om te verversen of het laden te starten in. Alles is aan te passen, inclusief een eigen naam en foto. Met een stekker-sensor per auto kiest hij zelf welke auto aan de laadpaal hangt; je laaddoel wordt ook in de auto gezet.
- **Auto wekken.** Begint een auto niet met laden, dan stuurt Easee Smart Charging na drie minuten een *hervatten* naar de laadpaal en zet de start-entiteit van de auto aan.
- **ERE-regeling.** Zet de ERE-regeling aan en vul in wat je per geladen kWh ontvangt; je ziet de opbrengst per maand, per jaar en totaal (ook in het maandrapport).
- **Boost.** Eén knop om direct op vol vermogen te laden, tot je de stekker eruit haalt.
- **Equalizer uitgelezen.** Netvermogen, stroom per fase (L1/L2/L3), spanning, belasting en resterende ruimte op je hoofdzekering, plus afname/teruglevering in kWh.
- **Kosten en vergoeding.** Kosten per sessie, dag en maand op basis van de echte prijs op dat moment. Optioneel een vergoedingstarief voor leaserijders, met een CSV-maandrapport voor je werkgever.
- **App-achtige kaart.** Een donkere kaart met de lichtstrip van de laadpaal als statuslampje (wit = stand-by, blauw = aangesloten, groen stromend = laden, amber = wacht op goedkoop moment, geel = zon, rood = fout). Tabbladen voor laden, planning met prijsgrafiek, Equalizer en historie.
- **Veilig.** Slimme sturing zet de laadstroom met een vervaltijd van 15 minuten. Valt Home Assistant uit, dan laadt je auto vanzelf weer normaal. Zonder prijsdata laadt hij gewoon direct.
- Nederlands, Engels en Duits.

Load balancing doet de Easee Equalizer zelf; deze integratie grijpt daar niet in.

## Installatie

1. Zorg dat de **Easee-integratie** draait ([nordicopen/easee_hass](https://github.com/nordicopen/easee_hass) via HACS).
2. Installeer **Easee Smart Charging** via HACS (knop hierboven) en herstart Home Assistant.
3. Ga naar *Instellingen → Apparaten & diensten → Integratie toevoegen → Easee Smart Charging* (of gebruik de tweede knop).
4. Kies je laadpaal (en Equalizer), controleer het herkende model, check je hoofdaansluiting (als je geen Equalizer hebt) en vul eventueel de opslag van je energiecontract in. Klaar.

Alle instellingen pas je later aan via *Configureren* op de integratie: laadpaal, hoofdaansluiting, prijzen en kosten (incl. ERE), auto's, en geavanceerd (minimale laadstroom, zonne-vertragingen, zonbuffer, laadrendement, auto verversen, taal).

Vink bij stap 4 *Benodigde Easee-sensoren automatisch inschakelen* aan: een paar Easee-sensoren (fasestromen, spanning, limieten) staan standaard uit.

## De kaart

De kaart wordt automatisch geladen; je hoeft niets aan je dashboard of resources te veranderen. Voeg hem toe via *Kaart toevoegen → Easee Smart Charging*, of in YAML:

```yaml
type: custom:easee-smart-card
entity: sensor.oprit_smart_status   # optioneel; zonder entity pakt hij de eerste laadpaal
tab: charge                         # charge | plan | grid | history
language: auto                      # auto | nl | en | de
```

### Losse kaarten

Naast de complete kaart zijn er losse kaarten om je dashboard zelf in te delen (allemaal in de kaartkiezer onder *Easee Smart Charging*):

| Kaart | Inhoud |
| --- | --- |
| `custom:easee-smart-charger-card` | Grote laadpaal met vermogen, lichtstrip-status, ERE/kosten en stroomprijs |
| `custom:easee-smart-modes-card` | Laadmodus, Boost en pauzeren/hervatten |
| `custom:easee-smart-cars-card` | Alle auto's met foto en accuniveau; tik om de actieve auto te kiezen |
| `custom:easee-smart-plan-card` | Vertrektijd, laaddoel en prijsgrafiek |
| `custom:easee-smart-grid-card` | Hoofdaansluiting of Equalizer |
| `custom:easee-smart-costs-card` | Kosten, ERE, sessies en export |

Elke kaart volgt je licht/donker thema (`theme: auto | light | dark`) en heeft een optionele `title`.

## Entiteiten

| Entiteit | Wat |
| --- | --- |
| `select … laadmodus` | Normaal, Slim, Zon, Zon + slim |
| `time … vertrektijd` | Moment waarop de auto klaar moet zijn |
| `number … te laden energie` / `doel accuniveau` | Hoeveel er bij moet |
| `number … altijd laden onder prijs` | Laad altijd als de prijs hieronder ligt (bijv. negatieve prijzen) |
| `switch … boost` | Nu laden op vol vermogen |
| `sensor … slim laden` | Wat de slimme sturing nu doet |
| `sensor … geplande start / klaar / kosten` | De planning |
| `sensor … kosten vandaag / deze maand / totaal` | Laadkosten |
| `sensor … geladen vandaag / deze maand` | Energie |
| `sensor … vergoeding deze maand` | Als je een vergoedingstarief hebt ingesteld |
| `sensor … netvermogen / zonne-overschot` | Met Equalizer of netsensor |
| `sensor … stroom fase L1-L3 / ruimte / belasting hoofdzekering` | Met Equalizer |
| `button … maandrapport exporteren` | CSV in `/config/www/easee_smart/` |

Acties: `easee_smart.export_report` (geeft het resultaat terug, handig in automatiseringen) en `easee_smart.set_mode`.

## Goed om te weten

- Zet in de Easee-app de eigen *slim laden* van Easee uit als je deze integratie de planning laat doen, anders sturen twee systemen tegelijk.
- Sommige auto's vallen in slaap tijdens een lange pauze. De integratie stuurt na drie minuten zonder stroom automatisch een *hervat*-commando.
- Kosten worden gerekend vanaf het moment dat de integratie draait; eerdere sessies staan niet in de historie.

Dit is een communityproject en geen officieel product van Easee.

---

## English

Smart charging, Equalizer insight, charging costs and an app-style dashboard card for Easee chargers, built on top of the existing Easee integration (no second login).

Pick your charger, set a departure time and how much energy you need, and Easee Smart Charging charges in the cheapest quarter hours (day-ahead EPEX SPOT prices for every European bidding zone are fetched automatically, no account needed), on solar surplus (via the Equalizer or any grid power sensor), or both. It reads all Equalizer values (grid power, per-phase current and voltage, main fuse load and headroom), tracks costs per session/day/month and exports a monthly CSV with optional reimbursement. The dynamic limit is always set with a 15-minute time-to-live, so the charger returns to normal if Home Assistant stops. Translated into English, Dutch and German.

Install: Easee integration first, then this repository via HACS, restart, add the *Easee Smart Charging* integration. The card (`custom:easee-smart-card`) is loaded automatically.

## Deutsch

Smartes Laden, Equalizer-Werte, Ladekosten und eine App-ähnliche Karte für Easee-Wallboxen, aufbauend auf der bestehenden Easee-Integration. Laden zu den günstigsten Stunden vor der Abfahrt, mit Solarüberschuss oder beides; alle Equalizer-Werte inklusive Phasenströme und Auslastung der Hauptsicherung; Kosten pro Ladevorgang und Monat mit CSV-Export. Installation: zuerst die Easee-Integration, dann dieses Repository über HACS.

## Bronnen

Prijsdata: [Energy-Charts](https://energy-charts.info) (Fraunhofer ISE), licentie CC BY 4.0.

## Licentie

MIT
