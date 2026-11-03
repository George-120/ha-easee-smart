"""Generate translations/en|nl|de.json and strings.json from one table."""
import json, pathlib

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
 "no_prices": T("Charging (no price sensor)","Laden (geen prijssensor)","Lädt (kein Preissensor)"),
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
}
MODELS = ["Easee Home","Easee Charge","Charge Lite","Charge Max","Charge Up","Charge Core","Charge Pro","Charge One"]

def build(lang):
    t = lambda x: x[lang]
    cfg_fields_energy = {
     "price_entity": T("Price sensor (dynamic tariff)","Prijssensor (dynamisch tarief)","Preissensor (dynamischer Tarif)"),
     "fixed_price": T("Fixed price (if no price sensor)","Vaste prijs (als er geen prijssensor is)","Festpreis (ohne Preissensor)"),
     "grid_power_entity": T("Grid power sensor (for solar surplus)","Netvermogen-sensor (voor zonne-overschot)","Netzleistungssensor (für Solarüberschuss)"),
     "grid_power_inverted": T("Sensor is positive when exporting","Sensor is positief bij teruglevering","Sensor ist positiv bei Einspeisung"),
     "soc_entity": T("Car battery level sensor (optional)","Accuniveau-sensor van de auto (optioneel)","Akkustand-Sensor des Autos (optional)"),
     "battery_capacity": T("Car battery capacity","Accucapaciteit auto","Akkukapazität Auto"),
     "reimbursement_per_kwh": T("Reimbursement rate (lease/employer)","Vergoedingstarief (lease/werkgever)","Erstattungssatz (Leasing/Arbeitgeber)"),
    }
    cfg_desc_energy = {
     "price_entity": T("Nordpool, Tibber, Frank Energie, Zonneplan, ENTSO-e… Prices for today/tomorrow are read automatically.",
                       "Nordpool, Tibber, Frank Energie, Zonneplan, ENTSO-e… De prijzen voor vandaag/morgen worden automatisch gelezen.",
                       "Nordpool, Tibber, ENTSO-e… Preise für heute/morgen werden automatisch gelesen."),
     "grid_power_entity": T("Only needed without an Easee Equalizer. Normally positive = import.","Alleen nodig zonder Easee Equalizer. Normaal positief = afname.","Nur ohne Easee Equalizer nötig. Normalerweise positiv = Bezug."),
     "reimbursement_per_kwh": T("Used for the monthly report of home charging.","Wordt gebruikt voor het maandrapport van thuisladen.","Wird für den Monatsbericht des Heimladens genutzt."),
    }
    cfg_fields_charger = {
     "model": T("Charger model","Laadpaalmodel","Wallbox-Modell"),
     "phases": T("Connection","Aansluiting","Anschluss"),
     "max_current": T("Maximum charge current","Maximale laadstroom","Maximaler Ladestrom"),
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
     "description": t(T("Tell Easee Smart where to see your grid connection, so it knows when solar power is left over. Found: {found}",
                        "Laat Easee Smart je hoofdaansluiting zien, zodat hij weet wanneer er zonnestroom over is. Gevonden: {found}",
                        "Zeige Easee Smart deinen Hausanschluss, damit erkannt wird, wann Solarstrom übrig ist. Gefunden: {found}")),
     "data": {k: t(v) for k, v in grid_fields.items()},
     "data_description": {k: t(v) for k, v in grid_desc.items()},
    }
    energy_step = {
     "title": t(T("Prices, car and costs","Prijzen, auto en kosten","Preise, Auto und Kosten")),
     "description": t(T("All optional. Without a price sensor smart charging just charges right away.",
                        "Alles optioneel. Zonder prijssensor laadt slim laden gewoon direct.",
                        "Alles optional. Ohne Preissensor lädt Smart-Laden sofort.")),
     "data": {k: t(v) for k, v in cfg_fields_energy.items() if k not in ("grid_power_entity", "grid_power_inverted")},
     "data_description": {k: t(v) for k, v in cfg_desc_energy.items() if k != "grid_power_entity"},
    }
    charger_opts = {
     "title": t(T("Charger","Laadpaal","Wallbox")),
     "data": {k: t(v) for k, v in cfg_fields_charger.items()},
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
       },
       "grid": grid_step,
       "energy": energy_step,
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
        "title": t(T("Easee Smart settings","Easee Smart-instellingen","Easee Smart-Einstellungen")),
        "menu_options": {
         "charger": t(T("Charger","Laadpaal","Wallbox")),
         "grid": t(T("Main connection","Hoofdaansluiting","Hausanschluss")),
         "energy": t(T("Prices, car and costs","Prijzen, auto en kosten","Preise, Auto und Kosten")),
        },
       },
       "charger": charger_opts,
       "grid": grid_step,
       "energy": energy_step,
      },
     },
     "selector": {
      "phases": {"options": {"1": t(T("1 phase","1 fase","1 Phase")), "3": t(T("3 phases","3 fasen","3 Phasen"))}},
      "charge_mode": {"options": {k: t(v) for k, v in MODES.items()}},
     },
     "entity": {
      "sensor": {k: {"name": t(v)} for k, v in SENSORS.items()},
      "binary_sensor": {
       "car_connected": {"name": t(T("Car connected","Auto aangesloten","Fahrzeug verbunden"))},
       "smart_active": {"name": t(T("Smart control active","Slimme sturing actief","Smarte Steuerung aktiv"))},
      },
      "select": {"charge_mode": {"name": t(T("Charge mode","Laadmodus","Lademodus")), "state": {k: t(v) for k, v in MODES.items()}}},
      "number": {
       "target_energy": {"name": t(T("Energy to add","Te laden energie","Zu ladende Energie"))},
       "target_soc": {"name": t(T("Target battery level","Doel accuniveau","Ziel-Akkustand"))},
       "price_threshold": {"name": t(T("Always charge below price","Altijd laden onder prijs","Immer laden unter Preis"))},
      },
      "time": {"departure_time": {"name": t(T("Departure time","Vertrektijd","Abfahrtszeit"))}},
      "switch": {"boost": {"name": t(T("Boost (charge now)","Boost (nu laden)","Boost (jetzt laden)"))}},
      "button": {"export_report": {"name": t(T("Export last month report","Maandrapport vorige maand exporteren","Bericht letzter Monat exportieren"))}},
     },
     "services": {
      "export_report": {
       "name": t(T("Export charging report","Laadrapport exporteren","Ladebericht exportieren")),
       "description": t(T("Writes a CSV with all sessions of a month to /config/www/easee_smart.","Schrijft een CSV met alle sessies van een maand naar /config/www/easee_smart.","Schreibt eine CSV mit allen Ladevorgängen eines Monats nach /config/www/easee_smart.")),
       "fields": {
        "config_entry_id": {"name": t(T("Charger","Laadpaal","Wallbox")), "description": t(T("Leave empty when you have one charger.","Leeg laten bij één laadpaal.","Leer lassen bei einer Wallbox."))},
        "month": {"name": t(T("Month","Maand","Monat")), "description": t(T("YYYY-MM, default: previous month.","JJJJ-MM, standaard: vorige maand.","JJJJ-MM, Standard: Vormonat."))},
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
      "no_charger": {"message": t(T("No Easee Smart charger is set up.","Er is geen Easee Smart-laadpaal ingesteld.","Keine Easee Smart-Wallbox eingerichtet."))},
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
