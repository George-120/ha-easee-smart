"""Generate translations/en|nl|de.json and strings.json from one table."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "easee_smart"
L = ("en", "nl", "de")

def T(en, nl, de):
    return {"en": en, "nl": nl, "de": de}

STATUS = {
 "disconnected": T("Disconnected","Niet verbonden","Nicht verbunden"),
 "awaiting_start": T("Waiting to start","Wacht op start","Wartet auf Start"),
 "charging": T("Charging","Laden","Lädt"),
 "completed": T("Completed","Voltooid","Abgeschlossen"),
 "error": T("Error","Fout","Fehler"),
 "ready_to_charge": T("Ready to charge","Klaar om te laden","Ladebereit"),
 "awaiting_authorization": T("Awaiting authorization","Wacht op autorisatie","Wartet auf Autorisierung"),
 "de_authorizing": T("De-authorizing","Autorisatie beëindigen","Deautorisierung"),
 "start_charging": T("Starting","Start laden","Startet"),
 "stop_charging": T("Stopping","Stopt laden","Stoppt"),
 "offline": T("Offline","Offline","Offline"),
 "awaiting_load_balancing": T("Awaiting load balancing","Wacht op load balancing","Wartet auf Lastmanagement"),
 "awaiting_smart_start": T("Awaiting smart start","Wacht op slimme start","Wartet auf Smart-Start"),
 "awaiting_scheduled_start": T("Awaiting scheduled start","Wacht op geplande start","Wartet auf geplanten Start"),
 "authenticating": T("Authenticating","Authenticeren","Authentifizierung"),
 "paused_due_to_equalizer": T("Paused by Equalizer","Gepauzeerd door Equalizer","Pausiert durch Equalizer"),
 "searching_for_master": T("Searching for master","Zoekt master","Sucht Master"),
 "erratic_ev": T("Erratic EV","Auto reageert onregelmatig","Fahrzeug unregelmäßig"),
 "error_temperature_too_high": T("Temperature too high","Temperatuur te hoog","Temperatur zu hoch"),
 "error_dead_powerboard": T("Power board failure","Powerboard defect","Leistungsplatine defekt"),
 "error_overcurrent": T("Overcurrent","Overstroom","Überstrom"),
 "error_pen_fault": T("PEN fault","PEN-fout","PEN-Fehler"),
 "unknown": T("Unknown","Onbekend","Unbekannt"),
}
SMART = {
 "idle": T("Off (normal charging)","Uit (normaal laden)","Aus (normales Laden)"),
 "not_connected": T("No car connected","Geen auto aangesloten","Kein Fahrzeug verbunden"),
 "waiting_cheap": T("Waiting for cheap hours","Wacht op goedkope uren","Wartet auf günstige Stunden"),
 "charging_cheap": T("Charging at a cheap moment","Laden op goedkoop moment","Lädt zum günstigen Zeitpunkt"),
 "charging_solar": T("Charging on solar surplus","Laden op zonne-overschot","Lädt mit Solarüberschuss"),
 "waiting_solar": T("Waiting for solar surplus","Wacht op zonne-overschot","Wartet auf Solarüberschuss"),
 "charging_boost": T("Boost: charging now","Boost: nu laden","Boost: lädt jetzt"),
 "charging_fallback": T("Charging (not enough price data)","Laden (te weinig prijsdata)","Lädt (zu wenig Preisdaten)"),
 "target_reached": T("Target reached","Doel bereikt","Ziel erreicht"),
 "no_prices": T("Charging (prices not available)","Laden (prijzen niet beschikbaar)","Lädt (keine Preise verfügbar)"),
}
MODES = {
 "normal": T("Normal","Normaal","Normal"),
 "smart": T("Smart (cheapest hours)","Slim (goedkoopste uren)","Smart (günstigste Stunden)"),
 "solar": T("Solar surplus","Zonne-overschot","Solarüberschuss"),
 "solar_smart": T("Solar + smart","Zon + slim","Solar + Smart"),
}
SENSORS = {
 "charger_status": T("Status","Status","Status"),
 "smart_status": T("Smart charging","Slim laden","Smart-Laden"),
 "target_current": T("Target current","Doelstroom","Zielstrom"),
 "energy_needed": T("Energy still needed","Nog benodigde energie","Noch benötigte Energie"),
 "planned_start": T("Planned start","Geplande start","Geplanter Start"),
 "planned_end": T("Planned finish","Gepland klaar","Geplantes Ende"),
 "planned_cost": T("Planned cost","Geplande kosten","Geplante Kosten"),
 "current_price": T("Current price","Huidige prijs","Aktueller Preis"),
 "session_cost": T("Session cost","Kosten sessie","Kosten Ladevorgang"),
 "cost_today": T("Cost today","Kosten vandaag","Kosten heute"),
 "cost_month": T("Cost this month","Kosten deze maand","Kosten diesen Monat"),
 "cost_total": T("Cost total","Kosten totaal","Kosten gesamt"),
 "energy_today": T("Charged today","Geladen vandaag","Heute geladen"),
 "energy_month": T("Charged this month","Geladen deze maand","Diesen Monat geladen"),
 "average_price_month": T("Average price this month","Gemiddelde prijs deze maand","Durchschnittspreis diesen Monat"),
 "reimbursement_month": T("Reimbursement this month","Vergoeding deze maand","Erstattung diesen Monat"),
 "last_session_energy": T("Last session energy","Energie laatste sessie","Energie letzter Ladevorgang"),
 "last_session_cost": T("Last session cost","Kosten laatste sessie","Kosten letzter Ladevorgang"),
 "grid_power": T("Grid power","Netvermogen","Netzleistung"),
 "surplus_power": T("Solar surplus","Zonne-overschot","Solarüberschuss"),
 "phase_l1_current": T("Phase L1 current","Stroom fase L1","Strom Phase L1"),
 "phase_l2_current": T("Phase L2 current","Stroom fase L2","Strom Phase L2"),
 "phase_l3_current": T("Phase L3 current","Stroom fase L3","Strom Phase L3"),
 "phase_headroom": T("Phase headroom","Ruimte op hoofdzekering","Reserve Hauptsicherung"),
 "phase_load": T("Main fuse load","Belasting hoofdzekering","Auslastung Hauptsicherung"),
 "car_soc": T("Car battery","Accu auto","Autoakku"),
 "ere_month": T("ERE this month","ERE deze maand","ERE diesen Monat"),
 "ere_year": T("ERE this year","ERE dit jaar","ERE dieses Jahr"),
 "ere_total": T("ERE total","ERE totaal","ERE gesamt"),
}
MODELS = ["Easee Home","Easee Charge","Charge Lite","Charge Max","Charge Up","Charge Core","Charge Pro","Charge One"]

def build(lang):
    t = lambda x: x[lang]
    cfg_fields_energy = {
     "bidding_zone": T("Price zone (day-ahead / APX)","Prijszone (day-ahead / APX)","Preiszone (Day-Ahead / EPEX)"),
     "price_resolution": T("Price per","Prijs per","Preis pro"),
     "price_markup": T("Supplier markup","Opslag leverancier","Aufschlag Lieferant"),
     "energy_tax": T("Energy tax (excl. VAT)","Energiebelasting (excl. btw)","Energiesteuer (ohne MwSt.)"),
     "vat_percent": T("VAT","Btw","MwSt."),
     "reimbursement_per_kwh": T("Reimbursement rate (lease/employer)","Vergoedingstarief (lease/werkgever)","Erstattungssatz (Leasing/Arbeitgeber)"),
     "ere_enabled": T("Track ERE revenue (emission reduction units)","ERE-regeling bijhouden (emissiereductie-eenheden)","ERE-Erlöse erfassen (Emissionsminderung)"),
     "ere_rate": T("ERE revenue per kWh","ERE-opbrengst per kWh","ERE-Erlös pro kWh"),
    }
    cfg_desc_energy = {
     "bidding_zone": T("Day-ahead market prices (EPEX SPOT, formerly APX) are fetched automatically for this zone, per quarter hour, for today and tomorrow. No account needed.",
                       "De day-ahead beursprijzen (EPEX SPOT, voorheen APX) worden automatisch per kwartier opgehaald voor vandaag en morgen. Geen account nodig.",
                       "Day-Ahead-Börsenpreise (EPEX SPOT) werden automatisch je Viertelstunde für heute und morgen abgerufen. Kein Konto nötig."),
     "price_resolution": T("Quarter hour is the most precise (market prices are per 15 minutes). Hour uses the average of the four quarters, like most hourly contracts.",
                           "Kwartier is het nauwkeurigst (de beurs rekent per 15 minuten). Uur neemt het gemiddelde van de vier kwartieren, zoals bij de meeste uurcontracten.",
                           "Viertelstunde ist am genauesten (Börsenpreise je 15 Minuten). Stunde nutzt den Mittelwert der vier Viertelstunden."),
     "price_markup": T("Per kWh, excl. VAT, from your dynamic contract.","Per kWh, excl. btw, uit je dynamische contract.","Pro kWh, ohne MwSt., aus deinem dynamischen Vertrag."),
     "energy_tax": T("Per kWh, excl. VAT. The consumer price is (market + markup + tax) × (1 + VAT).",
                     "Per kWh, excl. btw. De prijs wordt (beurs + opslag + belasting) × (1 + btw).",
                     "Pro kWh, ohne MwSt. Preis = (Börse + Aufschlag + Steuer) × (1 + MwSt.)."),
     "reimbursement_per_kwh": T("Used for the monthly report of home charging.","Wordt gebruikt voor het maandrapport van thuisladen.","Wird für den Monatsbericht des Heimladens genutzt."),
     "ere_rate": T("What you receive per charged kWh. Shown per month, per year and in total.","Wat je per geladen kWh ontvangt. Wordt getoond per maand, per jaar en totaal.","Was du pro geladener kWh erhältst. Pro Monat, Jahr und gesamt."),
    }
    cfg_fields_charger = {
     "model": T("Charger model","Laadpaalmodel","Wallbox-Modell"),
     "phases": T("Connection","Aansluiting","Anschluss"),
     "max_current": T("Maximum charge current","Maximale laadstroom","Maximaler Ladestrom"),
     "phase_switching": T("Automatic 1/3-phase switching for solar charging","Automatisch wisselen tussen 1 en 3 fasen bij zonneladen","Automatische 1/3-Phasen-Umschaltung beim Solarladen"),
     "session_mode": T("Charge mode for a new session","Laadmodus bij een nieuwe sessie","Lademodus bei neuer Ladesitzung"),
     "no_prices_action": T("When no prices are available (Smart)","Als er geen prijzen zijn (Slim)","Wenn keine Preise verfügbar sind (Smart)"),
    }
    cfg_desc_charger = {
     "phases": T("How your charger is connected. With 3 phases the charger can still charge on 1 phase.","Hoe je laadpaal is aangesloten. Bij 3 fasen kan de laadpaal ook op 1 fase laden.","Wie die Wallbox angeschlossen ist. Mit 3 Phasen kann sie auch einphasig laden."),
     "max_current": T("Per phase. Easee chargers charge from 6 A: 1.4 kW on 1 phase, 4.1 kW on 3 phases.","Per fase. Easee-laadpalen laden vanaf 6 A: 1,4 kW op 1 fase, 4,1 kW op 3 fasen.","Pro Phase. Easee-Wallboxen laden ab 6 A: 1,4 kW einphasig, 4,1 kW dreiphasig."),
     "phase_switching": T("With little sun the charger switches to 1 phase (from 1.4 kW); with enough sun back to 3 phases (from 4.1 kW). Normal, Smart and Boost always use 3 phases.",
                          "Bij weinig zon schakelt de laadpaal naar 1 fase (vanaf 1,4 kW), bij genoeg zon terug naar 3 fasen (vanaf 4,1 kW). Normaal, Slim en Boost laden altijd op 3 fasen.",
                          "Bei wenig Sonne schaltet die Wallbox auf 1 Phase (ab 1,4 kW), bei genug Sonne zurück auf 3 Phasen (ab 4,1 kW). Normal, Smart und Boost laden immer dreiphasig."),
     "session_mode": T("Each time a car is plugged in, the charge mode switches to this. 'Keep last mode' changes nothing.",
                       "Elke keer dat er een auto wordt aangesloten, springt de laadmodus naar deze stand. 'Laatste stand houden' verandert niets.",
                       "Bei jedem Anstecken springt der Lademodus auf diese Einstellung. 'Letzten Modus behalten' ändert nichts."),
     "no_prices_action": T("Prices for tomorrow come around 13:00. Without prices Smart can charge right away (the car is never left empty) or wait until prices arrive.",
                           "De prijzen voor morgen komen rond 13:00. Zonder prijzen kan Slim meteen laden (je auto staat nooit leeg) of wachten tot de prijzen er zijn.",
                           "Die Preise für morgen kommen gegen 13:00. Ohne Preise kann Smart sofort laden (das Auto bleibt nie leer) oder warten, bis Preise da sind."),
    }
    grid_fields = {
     "grid_import_entity": T("Grid import power (from grid)","Afname van het net (vermogen)","Netzbezug (Leistung)"),
     "grid_export_entity": T("Grid export power (to grid)","Teruglevering aan het net (vermogen)","Netzeinspeisung (Leistung)"),
     "grid_power_entity": T("Or: one net power sensor","Of: één netvermogen-sensor","Oder: ein Netzleistungssensor"),
     "grid_power_inverted": T("Net sensor is positive when exporting","Netsensor is positief bij teruglevering","Netzsensor ist positiv bei Einspeisung"),
     "phase_l1_entity": T("Current phase L1 (optional)","Stroom fase L1 (optioneel)","Strom Phase L1 (optional)"),
     "phase_l2_entity": T("Current phase L2 (optional)","Stroom fase L2 (optioneel)","Strom Phase L2 (optional)"),
     "phase_l3_entity": T("Current phase L3 (optional)","Stroom fase L3 (optioneel)","Strom Phase L3 (optional)"),
     "main_fuse": T("Main fuse","Hoofdzekering","Hauptsicherung"),
    }
    grid_desc = {
     "grid_import_entity": T("From your smart meter (P1). Detected sensors are filled in already.","Van je slimme meter (P1). Gevonden sensoren zijn al ingevuld.","Vom Smart Meter (P1). Gefundene Sensoren sind bereits eingetragen."),
     "grid_power_entity": T("Use this only when your meter has a single net power value (positive = import).","Alleen gebruiken als je meter één netto waarde geeft (positief = afname).","Nur nutzen, wenn der Zähler einen Nettowert liefert (positiv = Bezug)."),
     "main_fuse": T("Amperes per phase, e.g. 25 for a 3×25 A connection.","Ampère per fase, bijvoorbeeld 25 bij een 3×25 A-aansluiting.","Ampere pro Phase, z. B. 25 bei 3×25 A."),
    }
    grid_step = {
     "title": t(T("Main connection","Hoofdaansluiting","Hausanschluss")),
     "description": t(T("Tell Easee Smart Charging where to see your grid connection, so it knows when solar power is left over. Found: {found}",
                        "Laat Easee Smart Charging je hoofdaansluiting zien, zodat hij weet wanneer er zonnestroom over is. Gevonden: {found}",
                        "Zeige Easee Smart Charging deinen Hausanschluss, damit erkannt wird, wann Solarstrom übrig ist. Gefunden: {found}")),
     "data": {k: t(v) for k, v in grid_fields.items()},
     "data_description": {k: t(v) for k, v in grid_desc.items()},
    }
    energy_step = {
     "title": t(T("Prices and costs","Prijzen en kosten","Preise und Kosten")),
     "description": t(T("Prices are fetched automatically. Fill in your contract's markup so costs match your bill.",
                        "De prijzen worden automatisch opgehaald. Vul de opslag van je contract in, dan kloppen de kosten met je rekening.",
                        "Preise werden automatisch abgerufen. Trage den Aufschlag deines Vertrags ein, damit die Kosten stimmen.")),
     "data": {k: t(v) for k, v in cfg_fields_energy.items()},
     "data_description": {k: t(v) for k, v in cfg_desc_energy.items()},
    }
    charger_opts = {
     "title": t(T("Charger","Laadpaal","Wallbox")),
     "data": {k: t(v) for k, v in cfg_fields_charger.items()},
     "data_description": {k: t(v) for k, v in cfg_desc_charger.items()},
    }
    car_detail_fields = {
     "name": T("Name","Naam","Name"),
     "image": T("Photo (URL or /local/…)","Foto (URL of /local/…)","Foto (URL oder /local/…)"),
     "soc": T("Battery level","Accuniveau","Akkustand"),
     "capacity": T("Battery capacity","Accucapaciteit","Akkukapazität"),
     "target": T("Charge to","Laden tot","Laden bis"),
     "plug": T("Plugged-in sensor","Stekker-sensor","Stecker-Sensor"),
     "start_entity": T("Start charging (switch, button or script)","Laden starten (schakelaar, knop of script)","Laden starten (Schalter, Taste oder Skript)"),
     "refresh_entity": T("Refresh car data (button, switch or script)","Gegevens auto verversen (knop, schakelaar of script)","Autodaten aktualisieren (Taste, Schalter oder Skript)"),
     "limit_entity": T("Charge limit in the car","Laadlimiet in de auto","Ladelimit im Auto"),
     "range_entity": T("Range","Actieradius","Reichweite"),
     "remove": T("Remove this car","Deze auto verwijderen","Dieses Auto entfernen"),
    }
    car_detail_desc = {
     "image": T("Put a photo in /config/www/ and use /local/name.png, or paste a web address.","Zet een foto in /config/www/ en vul /local/naam.png in, of plak een webadres.","Foto in /config/www/ ablegen und /local/name.png eintragen, oder eine Webadresse."),
     "plug": T("Lets Easee Smart Charging see which car is connected.","Hiermee ziet Easee Smart Charging welke auto aan de laadpaal hangt.","Damit erkennt Easee Smart Charging, welches Auto angeschlossen ist."),
     "start_entity": T("Turned on when the car does not start charging by itself (sleeping cars).","Wordt aangezet als de auto niet vanzelf begint met laden (slapende auto's).","Wird eingeschaltet, wenn das Auto nicht von selbst lädt."),
     "limit_entity": T("Your 'charge to' target is also set in the car.","Je 'laden tot'-doel wordt ook in de auto gezet.","Dein Ladeziel wird auch im Auto gesetzt."),
    }
    device_field = {"device_id": t(T("Car (device)","Auto (apparaat)","Auto (Gerät)"))}
    device_desc = {"device_id": t(T("Pick your car from any integration. Its sensors are filled in automatically; you can change everything.",
                                    "Kies je auto uit elke integratie. De sensoren worden automatisch ingevuld; je kunt alles aanpassen.",
                                    "Wähle dein Auto aus einer beliebigen Integration. Die Sensoren werden automatisch eingetragen."))}
    car_details_step = {
     "title": t(T("Car","Auto","Auto")),
     "description": t(T("Everything except the name is optional. Works with every brand.","Alles behalve de naam is optioneel. Werkt met elk merk.","Alles außer dem Namen ist optional. Funktioniert mit jeder Marke.")),
     "data": {k: t(v) for k, v in car_detail_fields.items()},
     "data_description": {k: t(v) for k, v in car_detail_desc.items()},
    }
    cars_setup_step = {
     "title": t(T("Link a car (optional)","Auto koppelen (optioneel)","Auto verbinden (optional)")),
     "description": t(T("Leave empty to skip. You can add up to six cars later under Configure → Cars.","Laat leeg om over te slaan. Later kun je tot zes auto's toevoegen via Configureren → Auto's.","Leer lassen zum Überspringen. Später bis zu sechs Autos unter Konfigurieren → Autos.")),
     "data": device_field, "data_description": device_desc,
    }
    cars_menu = {
     "title": t(T("Cars","Auto's","Autos")),
     "menu_options": {
      "car_add": t(T("Add a car","Auto toevoegen","Auto hinzufügen")),
      "car_pick": t(T("Change or remove a car","Auto wijzigen of verwijderen","Auto ändern oder entfernen")),
     },
    }
    car_add_step = {"title": t(T("Add a car","Auto toevoegen","Auto hinzufügen")), "data": device_field, "data_description": device_desc}
    car_pick_step = {"title": t(T("Which car?","Welke auto?","Welches Auto?")), "data": {"car": t(T("Car","Auto","Auto"))}}
    adv_fields = {
     "min_current": T("Minimum charge current","Minimale laadstroom","Minimaler Ladestrom"),
     "solar_start_delay": T("Solar: start after surplus lasts","Zon: starten na overschot van","Solar: Start nach Überschuss von"),
     "solar_stop_delay": T("Solar: stop after shortage lasts","Zon: stoppen na tekort van","Solar: Stopp nach Defizit von"),
     "solar_buffer": T("Solar: keep exporting at least","Zon: minimaal blijven terugleveren","Solar: mindestens weiter einspeisen"),
     "charge_efficiency": T("Charging efficiency","Laadrendement","Ladewirkungsgrad"),
     "boost_reset_on_unplug": T("Turn Boost off when the car is unplugged","Boost uitzetten als de auto wordt losgekoppeld","Boost ausschalten beim Abstecken"),
     "resume_nudge": T("Wake the car when it does not start charging","Auto wekken als hij niet begint met laden","Auto wecken, wenn es nicht lädt"),
     "car_refresh_minutes": T("Refresh car data every (0 = off)","Gegevens auto verversen elke (0 = uit)","Autodaten aktualisieren alle (0 = aus)"),
     "language": T("Language of card and report","Taal van kaart en rapport","Sprache von Karte und Bericht"),
    }
    adv_desc = {
     "min_current": T("Most cars need at least 6 A. Some charge more efficiently from 8 or 10 A.","De meeste auto's hebben minimaal 6 A nodig. Sommige laden efficiënter vanaf 8 of 10 A.","Die meisten Autos brauchen mindestens 6 A."),
     "charge_efficiency": T("Energy lost while charging; used to calculate how much energy is still needed.","Verlies tijdens het laden; wordt gebruikt om te berekenen hoeveel energie er nog nodig is.","Ladeverluste; für die Berechnung der benötigten Energie."),
     "resume_nudge": T("After 3 minutes without charging: resume on the charger and the car's start entity.","Na 3 minuten zonder laden: hervatten op de laadpaal en de start-entiteit van de auto.","Nach 3 Minuten ohne Laden: Fortsetzen an der Wallbox und Start-Entität des Autos."),
     "car_refresh_minutes": T("Only while a car is connected. Uses the car's refresh entity.","Alleen als er een auto aangesloten is. Gebruikt de verversen-entiteit van de auto.","Nur wenn ein Auto angeschlossen ist."),
    }
    adv_step = {
     "title": t(T("Advanced","Geavanceerd","Erweitert")),
     "data": {k: t(v) for k, v in adv_fields.items()},
     "data_description": {k: t(v) for k, v in adv_desc.items()},
    }
    data = {
     "config": {
      "step": {
       "user": {
        "title": t(T("Choose your Easee charger","Kies je Easee-laadpaal","Wähle deine Easee-Wallbox")),
        "description": t(T("Pick the charger from the Easee integration. Nothing has to be entered by hand.",
                           "Kies de laadpaal uit de Easee-integratie. Je hoeft niets handmatig in te voeren.",
                           "Wähle die Wallbox aus der Easee-Integration. Nichts muss manuell eingegeben werden.")),
        "data": {
         "charger_device": t(T("Charger","Laadpaal","Wallbox")),
         "equalizer_device": t(T("Easee Equalizer (optional)","Easee Equalizer (optioneel)","Easee Equalizer (optional)")),
         "enable_source_entities": t(T("Enable the Easee sensors this integration needs","Benodigde Easee-sensoren automatisch inschakelen","Benötigte Easee-Sensoren automatisch aktivieren")),
        },
        "data_description": {
         "enable_source_entities": t(T("Some Easee sensors (current, voltage, limits) are disabled by default. Enabling them makes all values available.",
                                       "Sommige Easee-sensoren (stroom, spanning, limieten) staan standaard uit. Door ze aan te zetten zijn alle waarden beschikbaar.",
                                       "Einige Easee-Sensoren (Strom, Spannung, Grenzen) sind standardmäßig deaktiviert.")),
        },
       },
       "charger": {
        "title": t(T("{name}","{name}","{name}")),
        "description": t(T("Detected model: **{detected}**. Check the settings below.","Herkend model: **{detected}**. Controleer de instellingen hieronder.","Erkanntes Modell: **{detected}**. Prüfe die Einstellungen.")),
        "data": {k: t(v) for k, v in cfg_fields_charger.items()},
        "data_description": {k: t(v) for k, v in cfg_desc_charger.items()},
       },
       "grid": grid_step,
       "energy": energy_step,
       "cars": cars_setup_step,
       "car_details": car_details_step,
      },
      "abort": {
       "easee_missing": t(T("Install and set up the Easee integration first (HACS: nordicopen/easee_hass).",
                            "Installeer en configureer eerst de Easee-integratie (HACS: nordicopen/easee_hass).",
                            "Installiere und richte zuerst die Easee-Integration ein (HACS: nordicopen/easee_hass).")),
       "no_chargers": t(T("No Easee chargers found in the Easee integration.","Geen Easee-laadpalen gevonden in de Easee-integratie.","Keine Easee-Wallboxen in der Easee-Integration gefunden.")),
       "already_configured": t(T("This charger is already set up.","Deze laadpaal is al ingesteld.","Diese Wallbox ist bereits eingerichtet.")),
      },
     },
     "options": {
      "step": {
       "init": {
        "title": t(T("Easee Smart Charging settings","Easee Smart-instellingen","Easee Smart-Einstellungen")),
        "description": t(T(
            "**Charge modes**\n- **Normal**: charges right away at full power, whatever the price.\n- **Smart**: charges in the cheapest hours so the car is ready at your departure time.\n- **Solar**: charges only on solar surplus (1 or 3 phases automatically), otherwise waits.\n- **Solar + smart**: uses solar surplus first; what is still needed is charged in the cheapest hours, so the car is ready on time.\n\nWork through the sections below once; each one explains its settings.",
            "**Laadmodi**\n- **Normaal**: laadt meteen op vol vermogen, wat de prijs ook is.\n- **Slim**: laadt in de goedkoopste uren, zodat de auto op je vertrektijd vol is.\n- **Zon**: laadt alleen met zonne-overschot (automatisch op 1 of 3 fasen), anders wacht hij.\n- **Zon + slim**: gebruikt eerst zonne-overschot; wat dan nog nodig is, laadt hij in de goedkoopste uren, zodat de auto op tijd vol is.\n\nLoop de onderdelen hieronder één keer door; bij elk onderdeel staat uitgelegd wat het doet.",
            "**Lademodi**\n- **Normal**: lädt sofort mit voller Leistung, egal zu welchem Preis.\n- **Smart**: lädt in den günstigsten Stunden, damit das Auto zur Abfahrt voll ist.\n- **Solar**: lädt nur mit Solarüberschuss (automatisch 1- oder 3-phasig), sonst wartet sie.\n- **Solar + Smart**: nutzt zuerst Solarüberschuss; was noch fehlt, wird in den günstigsten Stunden geladen.\n\nGeh die Abschnitte unten einmal durch; jeder erklärt seine Einstellungen.")),
        "menu_options": {
         "charger": t(T("Charger: phases, current and default mode","Laadpaal: fasen, stroom en standaardmodus","Wallbox: Phasen, Strom und Standardmodus")),
         "equalizer": t(T("Easee Equalizer","Easee Equalizer","Easee Equalizer")),
         "grid": t(T("Main connection: smart meter for solar charging","Hoofdaansluiting: slimme meter voor zonneladen","Hausanschluss: Smart Meter fürs Solarladen")),
         "energy": t(T("Prices, ERE and costs","Prijzen, ERE en kosten","Preise, ERE und Kosten")),
         "cars": t(T("Cars: add, change or remove","Auto's: toevoegen, wijzigen of verwijderen","Autos: hinzufügen, ändern oder entfernen")),
         "advanced": t(T("Advanced: solar timing, buffer, language","Geavanceerd: zon-timing, buffer, taal","Erweitert: Solar-Timing, Puffer, Sprache")),
         "dashboard": t(T("Create the ready-made dashboard","Kant-en-klaar dashboard aanmaken","Fertiges Dashboard erstellen")),
        },
       },
       "equalizer": {
        "title": t(T("Easee Equalizer","Easee Equalizer","Easee Equalizer")),
        "description": t(T("Do you have an Easee Equalizer? Pick it here; when nothing is filled in yet, the Equalizer the Easee integration knows is picked for you. Found: {found}.",
                           "Heb je een Easee Equalizer? Kies hem hier; als er nog niets is ingevuld, staat de Equalizer die de Easee-integratie kent al klaar. Gevonden: {found}.",
                           "Hast du einen Easee Equalizer? Wähle ihn hier; ist noch nichts ausgefüllt, ist der Equalizer der Easee-Integration schon vorausgewählt. Gefunden: {found}.")),
        "data": {
         "equalizer_device": t(T("Equalizer","Equalizer","Equalizer")),
         "show_equalizer": t(T("Show in the cards","Tonen in de kaarten","In den Karten anzeigen")),
        },
        "data_description": {
         "equalizer_device": t(T("Choose — if you don't have one. With an Equalizer, solar charging uses its measurements instead of a meter.",
                                 "Kies — als je er geen hebt. Met een Equalizer gebruikt laden op zon zijn metingen in plaats van een meter.",
                                 "Wähle —, wenn du keinen hast. Mit Equalizer nutzt Solarladen dessen Messwerte statt eines Zählers.")),
         "show_equalizer": t(T("Automatic shows it as soon as an Equalizer is linked.","Automatisch laat hem zien zodra er een Equalizer gekoppeld is.","Automatisch zeigt ihn, sobald ein Equalizer verbunden ist.")),
        },
       },
       "dashboard": {
        "title": t(T("Create dashboard","Dashboard aanmaken","Dashboard erstellen")),
        "description": t(T("Adds a ready-made **Easee Smart** dashboard with all cards to your sidebar. Your own dashboards are never overwritten. Already created by this integration? Then it is refreshed with your current cars and settings.",
                           "Zet een kant-en-klaar **Easee Smart**-dashboard met alle kaarten in je zijbalk. Je eigen dashboards worden nooit overschreven. Heeft deze integratie het al eerder gemaakt? Dan wordt het bijgewerkt met je huidige auto's en instellingen.",
                           "Fügt ein fertiges **Easee Smart**-Dashboard mit allen Karten zur Seitenleiste hinzu. Deine eigenen Dashboards werden nie überschrieben. Hat diese Integration es schon erstellt? Dann wird es mit deinen aktuellen Autos und Einstellungen aktualisiert.")),
       },
       "charger": charger_opts,
       "grid": grid_step,
       "energy": energy_step,
       "cars": cars_menu,
       "car_add": car_add_step,
       "car_pick": car_pick_step,
       "car_details": car_details_step,
       "advanced": adv_step,
      },
      "error": {
       "dashboard_failed": t(T("The dashboard could not be created. Check the log for details.","Het dashboard kon niet worden aangemaakt. Kijk in het logboek voor details.","Das Dashboard konnte nicht erstellt werden. Details stehen im Protokoll.")),
      },
      "abort": {
       "dashboard_created": t(T("Done! Open **Easee Smart** in the sidebar ({url}).","Klaar! Open **Easee Smart** in de zijbalk ({url}).","Fertig! Öffne **Easee Smart** in der Seitenleiste ({url}).")),
      },
     },
     "selector": {
      "phases": {"options": {"1": t(T("1 phase","1 fase","1 Phase")), "3": t(T("3 phases","3 fasen","3 Phasen"))}},
      "charge_mode": {"options": {k: t(v) for k, v in MODES.items()}},
      "session_mode": {"options": {"keep": t(T("Keep last mode","Laatste stand houden","Letzten Modus behalten")), **{k: t(v) for k, v in MODES.items()}}},
      "no_prices_action": {"options": {"charge": t(T("Charge right away","Meteen laden","Sofort laden")), "wait": t(T("Wait for prices","Wachten op prijzen","Auf Preise warten"))}},
      "price_resolution": {"options": {"quarter": t(T("Quarter hour (15 min)","Kwartier (15 min)","Viertelstunde (15 Min.)")), "hour": t(T("Hour","Uur","Stunde"))}},
      "show_equalizer": {"options": {"auto": t(T("Automatic","Automatisch","Automatisch")), "show": t(T("Show","Tonen","Anzeigen")), "hide": t(T("Hide","Verbergen","Ausblenden"))}},
      "language": {"options": {"auto": t(T("Automatic (Home Assistant)","Automatisch (Home Assistant)","Automatisch (Home Assistant)")), "nl": "Nederlands", "en": "English", "de": "Deutsch"}},
     },
     "entity": {
      "sensor": {k: {"name": t(v)} for k, v in SENSORS.items()},
      "binary_sensor": {
       "car_connected": {"name": t(T("Car connected","Auto aangesloten","Fahrzeug verbunden"))},
       "smart_active": {"name": t(T("Smart control active","Slimme sturing actief","Smarte Steuerung aktiv"))},
      },
      "select": {
       "charge_mode": {"name": t(T("Charge mode","Laadmodus","Lademodus")), "state": {k: t(v) for k, v in MODES.items()}},
       "active_car": {"name": t(T("Connected car","Aangesloten auto","Angeschlossenes Auto")), "state": {"auto": t(T("Automatic","Automatisch","Automatisch"))}},
      },
      "number": {
       "target_energy": {"name": t(T("Energy to add","Te laden energie","Zu ladende Energie"))},
       "target_soc": {"name": t(T("Target battery level","Doel accuniveau","Ziel-Akkustand"))},
       "price_threshold": {"name": t(T("Always charge below price","Altijd laden onder prijs","Immer laden unter Preis"))},
      },
      "time": {"departure_time": {"name": t(T("Departure time","Vertrektijd","Abfahrtszeit"))}},
      "switch": {"boost": {"name": t(T("Boost (charge now)","Boost (nu laden)","Boost (jetzt laden)"))}},
      "button": {
       "export_report": {"name": t(T("Export last month report","Maandrapport vorige maand exporteren","Bericht letzter Monat exportieren"))},
       "refresh_car": {"name": t(T("Refresh car data","Gegevens auto verversen","Autodaten aktualisieren"))},
       "start_car": {"name": t(T("Start charging in car","Laden starten in auto","Laden im Auto starten"))},
      },
     },
     "services": {
      "export_report": {
       "name": t(T("Export charging report","Laadrapport exporteren","Ladebericht exportieren")),
       "description": t(T("Returns a CSV with all sessions of a month as the action response (nothing is stored on disk).","Geeft een CSV met alle sessies van een maand terug als antwoord van de actie (er wordt niets op schijf opgeslagen).","Gibt eine CSV mit allen Ladevorgängen eines Monats als Antwort der Aktion zurück (nichts wird gespeichert).")),
       "fields": {
        "config_entry_id": {"name": t(T("Charger","Laadpaal","Wallbox")), "description": t(T("Leave empty when you have one charger.","Leeg laten bij één laadpaal.","Leer lassen bei einer Wallbox."))},
        "month": {"name": t(T("Month","Maand","Monat")), "description": t(T("YYYY-MM, default: previous month.","JJJJ-MM, standaard: vorige maand.","JJJJ-MM, Standard: Vormonat."))},
       },
      },
      "create_dashboard": {
       "name": t(T("Create dashboard","Dashboard aanmaken","Dashboard erstellen")),
       "description": t(T("Adds the ready-made Easee Smart dashboard with all cards to the sidebar, or refreshes the one this integration created. Admins only; your own dashboards are never overwritten.","Zet het kant-en-klare Easee Smart-dashboard met alle kaarten in de zijbalk, of werkt het dashboard bij dat deze integratie zelf heeft gemaakt. Alleen voor beheerders; je eigen dashboards worden nooit overschreven.","Fügt das fertige Easee Smart-Dashboard mit allen Karten zur Seitenleiste hinzu oder aktualisiert das von dieser Integration erstellte. Nur für Administratoren; eigene Dashboards werden nie überschrieben.")),
       "fields": {
        "config_entry_id": {"name": t(T("Charger","Laadpaal","Wallbox")), "description": t(T("Leave empty when you have one charger.","Leeg laten bij één laadpaal.","Leer lassen bei einer Wallbox."))},
       },
      },
      "set_mode": {
       "name": t(T("Set charge mode","Laadmodus instellen","Lademodus setzen")),
       "description": t(T("Switch between normal, smart, solar and solar + smart.","Wissel tussen normaal, slim, zon en zon + slim.","Wechsel zwischen Normal, Smart, Solar und Solar + Smart.")),
       "fields": {
        "config_entry_id": {"name": t(T("Charger","Laadpaal","Wallbox")), "description": t(T("Leave empty when you have one charger.","Leeg laten bij één laadpaal.","Leer lassen bei einer Wallbox."))},
        "mode": {"name": t(T("Mode","Modus","Modus")), "description": t(T("The new charge mode.","De nieuwe laadmodus.","Der neue Lademodus."))},
       },
      },
     },
     "exceptions": {
      "dashboard_failed": {"message": t(T("The dashboard could not be created: {error}","Het dashboard kon niet worden aangemaakt: {error}","Das Dashboard konnte nicht erstellt werden: {error}"))},
      "no_charger": {"message": t(T("No Easee Smart Charging charger is set up.","Er is geen Easee Smart-laadpaal ingesteld.","Keine Easee Smart-Wallbox eingerichtet."))},
      "easee_not_loaded": {"message": t(T("The Easee integration is not loaded yet.","De Easee-integratie is nog niet geladen.","Die Easee-Integration ist noch nicht geladen."))},
      "charger_not_found": {"message": t(T("The charger was not found in the Easee integration.","De laadpaal is niet gevonden in de Easee-integratie.","Die Wallbox wurde in der Easee-Integration nicht gefunden."))},
     },
    }
    data["entity"]["sensor"]["charger_status"]["state"] = {k: t(v) for k, v in STATUS.items()}
    data["entity"]["sensor"]["smart_status"]["state"] = {k: t(v) for k, v in SMART.items()}
    return data

(ROOT / "translations").mkdir(exist_ok=True)
for lang in L:
    (ROOT / "translations" / f"{lang}.json").write_text(json.dumps(build(lang), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(ROOT / "strings.json").write_text(json.dumps(build("en"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("ok")
