/* Easee Smart Charging card — app-style view of an Easee charger, served by the easee_smart integration. */
(() => {
  const VERSION = "1.11.6";
  // Photo of the charger, served next to this script by the integration.
  const CHARGER_IMG = document.currentScript && document.currentScript.src
    ? new URL("charger.webp", document.currentScript.src).href
    : "/easee_smart/charger.webp";
  const EQ_IMG = CHARGER_IMG.replace(/charger\.webp(\?.*)?$/, "equalizer.webp");

  const I18N = {
    en: {
      tabs: { charge: "Charging", plan: "Planning", grid: "Equalizer", meter: "Grid", history: "History" },
      modes: { normal: "Normal", smart: "Smart", solar: "Solar", solar_smart: "Solar + smart" }, modeDesc: { normal: "Charges right away at full power, whatever the price.", smart: "Charges in the cheapest hours so the car is ready at your departure time.", solar: "Charges only on solar surplus, on 1 or 3 phases automatically.", solar_smart: "Solar surplus first; what is still needed is charged in the cheapest hours." }, modeNow: "Mode", phase1: "1 phase", phase3: "3 phases", chartNormal: "Normal: charges whenever the car is plugged in, at any price.", chartSolar: "Solar: charges only on surplus; the price does not matter.", chartSolarSmart: "Solar + smart: sun first (yellow); the rest in the blue cheap hours.", sunFirst: "sun first", cheapHours: "cheap hours", noPricesWait: "No prices yet: Smart waits until they arrive.", sunForecast: "solar forecast", sunCharge: "charging on sun", sunToday: "Sun today", sunTomorrow: "Sun tomorrow", tomorrowShort: "tomorrow", perQuarter: "per quarter hour", yesterday: "Yesterday", tomorrowCap: "Tomorrow", nowCap: "Now", sunReal: "sun measured", pricesLater: "Prices for tomorrow come around 13:00", fromSun: "from the sun", solidLight: "solid = charged, light = expected", expected: "expected", sunUntil: "Sun until departure", fromGrid: "From the grid", chargeable: "chargeable", whatWillHappen: "What the system will do", planSun: "Expects {sun} kWh of sun before {time}; buys {grid} kWh from the grid in the cheapest hours.", planSunOnly: "Expects {sun} kWh of sun before {time}; that covers what is needed.", planSolarOnly: "Charges only on the sun: about {sun} kWh before {time}.", forecastLearning: "Forecast is still learning from your history.",
      status: {
        disconnected: "No car connected", awaiting_start: "Waiting to start", charging: "Charging",
        completed: "Charging complete", error: "Error", ready_to_charge: "Ready to charge",
        awaiting_authorization: "Waiting for authorization", offline: "Charger offline",
        awaiting_load_balancing: "Waiting for load balancing", awaiting_smart_start: "Waiting for smart start",
        awaiting_scheduled_start: "Waiting for schedule", paused_due_to_equalizer: "Paused by Equalizer",
        unknown: "Unknown",
      },
      smart: {
        idle: "Charges as soon as the car is connected", not_connected: "Connect the car to start",
        waiting_cheap: "Waiting for the cheapest moment", charging_cheap: "Charging at a cheap moment",
        charging_solar: "Charging on solar surplus", waiting_solar: "Waiting for solar surplus",
        charging_boost: "Boost: charging at full power", charging_fallback: "Charging now, not enough price data",
        target_reached: "Target reached", no_prices: "Prices not available, charging now",
      },
      pause: "Pause", resume: "Resume", start: "Start", boost: "Boost", lock: "Lock cable", unlock: "Cable unlocked",
      session: "this session", cost: "cost", duration: "time",
      departure: "Ready at", target: "Add", targetSoc: "Charge to", unitPct: "%", unitKwh: "kWh", byPct: "Charge to a battery %", byKwh: "Charge a fixed number of kWh", needed: "still needed",
      planStart: "Starts", planEnd: "Ready", planCost: "Estimated", noPlan: "No plan needed right now.", tooShort: "Not possible before {dep}: at {kw} kW only {fit} kWh fits until then, {need} kWh is needed (about {dur} of charging). Set \u201cReady at\u201d later or use Boost.",
      noPrices: "Prices could not be fetched yet. They update automatically.",
      now: "now", grid: "Grid", importing: "Importing", exporting: "Exporting", fuse: "Main fuse",
      headroom: "headroom", surplus: "Solar surplus", phase: "Phase", noGrid: "No Equalizer or main connection set. Add your meter under Configure → Main connection.",
      month: "This month", prev: "Previous months", reimb: "Reimbursement", sessions: "Recent sessions",
      export: "Export last month (CSV)", exported: "Report written", today: "Today", none: "No sessions yet.",
      kwh: "kWh", avg: "avg.", amps: "Charge current", planned: "Planned charging", preview: "Preview: this is how Smart would plan it. Choose Smart (or Solar + smart) to use it.", solarStart: "starts from", solarNone: "No surplus right now", solarAvail: "Solar available", eqTitle: "Equalizer", eqOnline: "Online", eqOffline: "Offline", eqLoad: "load", eqLoadT: "Load", eqLimit: "Max. continuous", eqFirmware: "Firmware", eqTemp: "Temperature", eqNone: "No Equalizer linked. Link it under Configure → Equalizer.", eqTotals: "Meter readings", eqPhases: "Phases", stale: "Easee Smart Charging was updated. Refresh the page to load the new cards.", reload: "Refresh", refresh: "Refresh car data", priceNow: "Power now", carsTitle: "Cars", noCars: "No cars linked yet. Add them under Configure → Cars.", pluggedIn: "Plugged in", notPlugged: "Not plugged in", ere: "ERE", year: "This year", total: "Total", range: "range",
    },
    nl: {
      tabs: { charge: "Laden", plan: "Planning", grid: "Equalizer", meter: "Aansluiting", history: "Historie" },
      modes: { normal: "Normaal", smart: "Slim", solar: "Zon", solar_smart: "Zon + slim" }, modeDesc: { normal: "Laadt meteen op vol vermogen, wat de prijs ook is.", smart: "Laadt in de goedkoopste uren, zodat de auto op je vertrektijd vol is.", solar: "Laadt alleen met zonne-overschot, automatisch op 1 of 3 fasen.", solar_smart: "Eerst zonne-overschot; wat dan nog nodig is, in de goedkoopste uren." }, modeNow: "Modus", phase1: "1 fase", phase3: "3 fasen", chartNormal: "Normaal: laadt zodra de auto is aangesloten, op elk moment en elke prijs.", chartSolar: "Zon: laadt alleen met overschot; de prijs speelt geen rol.", chartSolarSmart: "Zon + slim: eerst zon (geel), de rest in de blauwe goedkope uren.", sunFirst: "eerst zon", cheapHours: "goedkope uren", noPricesWait: "Nog geen prijzen: Slim wacht tot ze er zijn.", sunForecast: "zonverwachting", sunCharge: "laden met zon", sunToday: "Zon vandaag", sunTomorrow: "Zon morgen", tomorrowShort: "morgen", perQuarter: "per kwartier", yesterday: "Gisteren", tomorrowCap: "Morgen", nowCap: "Nu", sunReal: "zon gemeten", pricesLater: "Prijzen voor morgen komen rond 13:00", fromSun: "van de zon", solidLight: "vol = geladen, licht = verwacht", expected: "verwacht", sunUntil: "Zon tot vertrek", fromGrid: "Van het net", chargeable: "laadbaar", whatWillHappen: "Wat het systeem gaat doen", planSun: "Verwacht {sun} kWh zon vóór {time}; haalt {grid} kWh van het net in de goedkoopste uren.", planSunOnly: "Verwacht {sun} kWh zon vóór {time}; dat is genoeg.", planSolarOnly: "Laadt alleen met zon: ongeveer {sun} kWh vóór {time}.", forecastLearning: "De verwachting leert nog van je geschiedenis.",
      status: {
        disconnected: "Geen auto aangesloten", awaiting_start: "Wacht op start", charging: "Laden",
        completed: "Laden voltooid", error: "Fout", ready_to_charge: "Klaar om te laden",
        awaiting_authorization: "Wacht op autorisatie", offline: "Laadpaal offline",
        awaiting_load_balancing: "Wacht op load balancing", awaiting_smart_start: "Wacht op slimme start",
        awaiting_scheduled_start: "Wacht op planning", paused_due_to_equalizer: "Gepauzeerd door Equalizer",
        unknown: "Onbekend",
      },
      smart: {
        idle: "Laadt zodra de auto is aangesloten", not_connected: "Sluit de auto aan om te starten",
        waiting_cheap: "Wacht op het goedkoopste moment", charging_cheap: "Laden op een goedkoop moment",
        charging_solar: "Laden op zonne-overschot", waiting_solar: "Wacht op zonne-overschot",
        charging_boost: "Boost: laden op vol vermogen", charging_fallback: "Nu laden, te weinig prijsdata",
        target_reached: "Doel bereikt", no_prices: "Prijzen niet beschikbaar, nu laden",
      },
      pause: "Pauzeren", resume: "Hervatten", start: "Starten", boost: "Boost", lock: "Kabel vast", unlock: "Kabel los",
      session: "deze sessie", cost: "kosten", duration: "tijd",
      departure: "Klaar om", target: "Laden", targetSoc: "Laden tot", unitPct: "%", unitKwh: "kWh", byPct: "Laden tot een accupercentage", byKwh: "Een vast aantal kWh laden", needed: "nog nodig",
      planStart: "Start", planEnd: "Klaar", planCost: "Verwacht", noPlan: "Er is nu geen planning nodig.", tooShort: "Niet haalbaar vóór {dep}: met {kw} kW past er tot dan maar {fit} kWh in, er is {need} kWh nodig (ongeveer {dur} laden). Zet \u201cKlaar om\u201d later of kies Boost.",
      noPrices: "De prijzen konden nog niet worden opgehaald. Ze worden vanzelf bijgewerkt.",
      now: "nu", grid: "Net", importing: "Afname", exporting: "Teruglevering", fuse: "Hoofdzekering",
      headroom: "ruimte", surplus: "Zonne-overschot", phase: "Fase", noGrid: "Geen Equalizer of hoofdaansluiting ingesteld. Voeg je meter toe via Configureren → Hoofdaansluiting.",
      month: "Deze maand", prev: "Vorige maanden", reimb: "Vergoeding", sessions: "Recente sessies",
      export: "Vorige maand exporteren (CSV)", exported: "Rapport opgeslagen", today: "Vandaag", none: "Nog geen sessies.",
      kwh: "kWh", avg: "gem.", amps: "Laadstroom", planned: "Gepland laden", preview: "Voorbeeld: zo plant Slim laden het. Kies Slim (of Zon + slim) om dit te gebruiken.", solarStart: "start vanaf", solarNone: "Nu geen overschot", solarAvail: "Zon beschikbaar", eqTitle: "Equalizer", eqOnline: "Online", eqOffline: "Offline", eqLoad: "belast", eqLoadT: "Belasting", eqLimit: "Max. continu", eqFirmware: "Firmware", eqTemp: "Temperatuur", eqNone: "Geen Equalizer gekoppeld. Koppel hem via Configureren → Equalizer.", eqTotals: "Meterstanden", eqPhases: "Fasen", stale: "Easee Smart Charging is bijgewerkt. Vernieuw de pagina om de nieuwe kaarten te laden.", reload: "Vernieuwen", refresh: "Gegevens auto verversen", priceNow: "Stroom nu", carsTitle: "Auto's", noCars: "Nog geen auto's gekoppeld. Voeg ze toe via Configureren → Auto's.", pluggedIn: "Aangesloten", notPlugged: "Niet aangesloten", ere: "ERE", year: "Dit jaar", total: "Totaal", range: "actieradius",
    },
    de: {
      tabs: { charge: "Laden", plan: "Planung", grid: "Equalizer", meter: "Anschluss", history: "Verlauf" },
      modes: { normal: "Normal", smart: "Smart", solar: "Solar", solar_smart: "Solar + Smart" }, modeDesc: { normal: "Lädt sofort mit voller Leistung, egal zu welchem Preis.", smart: "Lädt in den günstigsten Stunden, damit das Auto zur Abfahrt voll ist.", solar: "Lädt nur mit Solarüberschuss, automatisch 1- oder 3-phasig.", solar_smart: "Zuerst Solarüberschuss; der Rest in den günstigsten Stunden." }, modeNow: "Modus", phase1: "1 Phase", phase3: "3 Phasen", chartNormal: "Normal: lädt, sobald das Auto angesteckt ist, zu jedem Preis.", chartSolar: "Solar: lädt nur mit Überschuss; der Preis spielt keine Rolle.", chartSolarSmart: "Solar + Smart: zuerst Sonne (gelb), der Rest in den blauen günstigen Stunden.", sunFirst: "zuerst Sonne", cheapHours: "günstige Stunden", noPricesWait: "Noch keine Preise: Smart wartet, bis sie da sind.", sunForecast: "Solarprognose", sunCharge: "Laden mit Sonne", sunToday: "Sonne heute", sunTomorrow: "Sonne morgen", tomorrowShort: "morgen", perQuarter: "pro Viertelstunde", yesterday: "Gestern", tomorrowCap: "Morgen", nowCap: "Jetzt", sunReal: "Sonne gemessen", pricesLater: "Preise für morgen kommen gegen 13:00", fromSun: "von der Sonne", solidLight: "voll = geladen, hell = erwartet", expected: "erwartet", sunUntil: "Sonne bis Abfahrt", fromGrid: "Aus dem Netz", chargeable: "ladbar", whatWillHappen: "Was das System tun wird", planSun: "Erwartet {sun} kWh Sonne vor {time}; kauft {grid} kWh in den günstigsten Stunden.", planSunOnly: "Erwartet {sun} kWh Sonne vor {time}; das reicht.", planSolarOnly: "Lädt nur mit Sonne: etwa {sun} kWh vor {time}.", forecastLearning: "Die Prognose lernt noch aus deinem Verlauf.",
      status: {
        disconnected: "Kein Fahrzeug verbunden", awaiting_start: "Wartet auf Start", charging: "Lädt",
        completed: "Laden abgeschlossen", error: "Fehler", ready_to_charge: "Ladebereit",
        awaiting_authorization: "Wartet auf Autorisierung", offline: "Wallbox offline",
        awaiting_load_balancing: "Wartet auf Lastmanagement", awaiting_smart_start: "Wartet auf Smart-Start",
        awaiting_scheduled_start: "Wartet auf Zeitplan", paused_due_to_equalizer: "Pausiert durch Equalizer",
        unknown: "Unbekannt",
      },
      smart: {
        idle: "Lädt, sobald das Auto verbunden ist", not_connected: "Auto verbinden, um zu starten",
        waiting_cheap: "Wartet auf den günstigsten Zeitpunkt", charging_cheap: "Lädt zum günstigen Zeitpunkt",
        charging_solar: "Lädt mit Solarüberschuss", waiting_solar: "Wartet auf Solarüberschuss",
        charging_boost: "Boost: lädt mit voller Leistung", charging_fallback: "Lädt jetzt, zu wenig Preisdaten",
        target_reached: "Ziel erreicht", no_prices: "Keine Preise verfügbar, lädt jetzt",
      },
      pause: "Pausieren", resume: "Fortsetzen", start: "Starten", boost: "Boost", lock: "Kabel verriegelt", unlock: "Kabel frei",
      session: "dieser Ladevorgang", cost: "Kosten", duration: "Dauer",
      departure: "Fertig um", target: "Laden", targetSoc: "Laden bis", unitPct: "%", unitKwh: "kWh", byPct: "Bis zu einem Akkustand laden", byKwh: "Eine feste kWh-Menge laden", needed: "noch nötig",
      planStart: "Start", planEnd: "Fertig", planCost: "Erwartet", noPlan: "Derzeit ist keine Planung nötig.", tooShort: "Bis {dep} nicht machbar: mit {kw} kW passen bis dahin nur {fit} kWh, nötig sind {need} kWh (etwa {dur} Laden). Stelle \u201eFertig um\u201c später ein oder nutze Boost.",
      noPrices: "Preise konnten noch nicht abgerufen werden. Sie werden automatisch aktualisiert.",
      now: "jetzt", grid: "Netz", importing: "Bezug", exporting: "Einspeisung", fuse: "Hauptsicherung",
      headroom: "Reserve", surplus: "Solarüberschuss", phase: "Phase", noGrid: "Kein Equalizer oder Hausanschluss eingerichtet. Zähler unter Konfigurieren → Hausanschluss hinzufügen.",
      month: "Dieser Monat", prev: "Vormonate", reimb: "Erstattung", sessions: "Letzte Ladevorgänge",
      export: "Letzten Monat exportieren (CSV)", exported: "Bericht gespeichert", today: "Heute", none: "Noch keine Ladevorgänge.",
      kwh: "kWh", avg: "Ø", amps: "Ladestrom", planned: "Geplantes Laden", preview: "Vorschau: so würde Smart planen. Wähle Smart (oder Solar + Smart), um es zu nutzen.", solarStart: "startet ab", solarNone: "Gerade kein Überschuss", solarAvail: "Solar verfügbar", eqTitle: "Equalizer", eqOnline: "Online", eqOffline: "Offline", eqLoad: "Last", eqLoadT: "Auslastung", eqLimit: "Max. Dauerstrom", eqFirmware: "Firmware", eqTemp: "Temperatur", eqNone: "Kein Equalizer verbunden. Unter Konfigurieren → Equalizer verbinden.", eqTotals: "Zählerstände", eqPhases: "Phasen", stale: "Easee Smart Charging wurde aktualisiert. Lade die Seite neu, um die neuen Karten zu laden.", reload: "Neu laden", refresh: "Autodaten aktualisieren", priceNow: "Strom jetzt", carsTitle: "Autos", noCars: "Noch keine Autos verbunden. Unter Konfigurieren → Autos hinzufügen.", pluggedIn: "Angeschlossen", notPlugged: "Nicht angeschlossen", ere: "ERE", year: "Dieses Jahr", total: "Gesamt", range: "Reichweite",
    },
  };

  const LED = {
    standby: "#E6EBF1",
    connected: "#5AA9FF",
    charging: "#45D69A",
    waiting: "#F4B740",
    solar: "#FFD54F",
    error: "#FF5C61",
    offline: "#59616D",
  };

  const CONNECTED = new Set([
    "awaiting_start", "charging", "completed", "ready_to_charge", "awaiting_authorization",
    "awaiting_load_balancing", "awaiting_smart_start", "awaiting_scheduled_start",
    "paused_due_to_equalizer", "start_charging", "stop_charging", "authenticating",
  ]);

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  class EaseeSmartCard extends HTMLElement {
    static getConfigElement() {
      return document.createElement("easee-smart-card-editor");
    }

    static getStubConfig(hass) {
      const entity = Object.keys(hass.states).find((id) => id.startsWith("sensor.") && hass.states[id].attributes.charger_id && hass.states[id].attributes.sources);
      return { entity: entity || "" };
    }

    setConfig(config) {
      this._config = { tab: "charge", ...(config || {}) };
      this._tab = this._tab || this._config.tab;
      this._sig = null;
      if (!this.shadowRoot) {
        this.attachShadow({ mode: "open" });
        this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
        this.shadowRoot.addEventListener("change", (e) => this._onChange(e));
        // The time field is saved when you leave it (click elsewhere) or press Enter, not while typing:
        // a native time input already reports "02:00" after the first digit of "20:00".
        this.shadowRoot.addEventListener("focusout", (e) => this._onLeave(e));
        this.shadowRoot.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && e.target && e.target.dataset && e.target.dataset.ctl) e.target.blur();
        });
      }
    }

    getCardSize() {
      return 7;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, rows: "auto" };
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._config) return; // preview: hass can arrive before setConfig
      const entityId = this._entityId();
      const st = entityId && hass.states[entityId];
      const a = st ? st.attributes : null;
      const ids = a ? [...Object.values(a.sources || {}), ...Object.values(a.equalizer || {}), ...Object.values(a.entities || {})] : [];
      const sig = JSON.stringify([this._config && this._config.language, this._tab, st && st.last_updated, a, ids.map((id) => hass.states[id] && hass.states[id].state), hass.locale && hass.locale.language]);
      if (sig === this._sig) return;
      this._sig = sig;
      if (this._editing()) { this._pending = true; return; }  // never redraw under the user's fingers
      this._render();
    }

    _editing() {
      const el = this.shadowRoot && this.shadowRoot.activeElement;
      return !!(el && el.dataset && el.dataset.ctl);
    }

    _entityId() {
      if (this._config && this._config.entity) return this._config.entity;
      if (!this._hass) return null;
      return Object.keys(this._hass.states).find((id) => id.startsWith("sensor.") && this._hass.states[id].attributes.charger_id && this._hass.states[id].attributes.sources);
    }

    get _lang() {
      // Card option "language" (nl / en / de) overrides the Home Assistant profile language.
      const forced = this._config && this._config.language && this._config.language !== "auto" ? this._config.language : null;
      const st = this._hass && this._entityId() && this._hass.states[this._entityId()];
      const integration = st && st.attributes.language && st.attributes.language !== "auto" ? st.attributes.language : null;
      return forced || integration || (this._hass && (this._hass.locale?.language || this._hass.language)) || "en";
    }

    get _t() {
      return I18N[this._lang.slice(0, 2)] || I18N.en;
    }

    _num(v, digits = 1) {
      if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "–";
      return Number(v).toLocaleString(this._lang, { minimumFractionDigits: digits, maximumFractionDigits: digits });
    }

    _money(v, currency) {
      if (v === null || v === undefined || isNaN(Number(v))) return "–";
      try {
        return Number(v).toLocaleString(this._lang, { style: "currency", currency: currency || "EUR" });
      } catch (e) {
        return this._num(v, 2);
      }
    }

    _time(iso) {
      if (!iso) return "–";
      return new Date(iso).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit" });
    }

    _day(iso) {
      if (!iso) return "";
      return new Date(iso).toLocaleDateString(this._lang, { weekday: "short", day: "numeric", month: "short" });
    }

    _state(id) {
      const s = id && this._hass.states[id];
      return s && !["unavailable", "unknown"].includes(s.state) ? s : null;
    }

    _val(id) {
      const s = this._state(id);
      return s ? Number(s.state) : null;
    }

    _ledFor(status, smart) {
      if (status === "offline" || status === "unknown") return { color: LED.offline, anim: "none" };
      if (String(status).startsWith("error") || status === "erratic_ev") return { color: LED.error, anim: "blink" };
      if (status === "charging") return { color: smart === "charging_solar" ? LED.solar : LED.charging, anim: "flow" };
      if (smart === "waiting_cheap") return { color: LED.waiting, anim: "breathe" };
      if (smart === "waiting_solar") return { color: LED.solar, anim: "breathe" };
      if (CONNECTED.has(status)) return { color: LED.connected, anim: status === "completed" ? "none" : "breathe" };
      return { color: LED.standby, anim: "none" };
    }

    // ------------------------------------------------------------------ render
    _render() {
      if (!this.shadowRoot || !this._hass) return;
      const entityId = this._entityId();
      const st = entityId && this._hass.states[entityId];
      if (!st) {
        this.shadowRoot.innerHTML = `<style>${CSS}</style><ha-card><div class="empty">Easee Smart Charging: ${esc(entityId || "no charger found")}</div></ha-card>`;
        return;
      }
      const a = st.attributes;
      const t = this._t;
      const src = a.sources || {};
      const status = st.state;
      const smart = a.smart_state;
      const led = this._ledFor(status, smart);
      const power = this._val(src.power);
      const online = this._state(src.online);
      const isOnline = online ? online.state === "on" : status !== "offline";
      const name = this._config.name || a.name || "Easee";
      const tabs = ["charge", "plan", "grid", "history"];
      const body = { charge: () => this._tabCharge(a, t, status), plan: () => this._tabPlan(a, t), grid: () => this._tabGrid(a, t), history: () => this._tabHistory(a, t) }[this._tab] || (() => "");

      const sessionStart = a.session && a.session.start ? new Date(a.session.start) : null;
      let duration = "–";
      if (sessionStart && CONNECTED.has(status)) {
        const mins = Math.max(0, Math.round((Date.now() - sessionStart.getTime()) / 60000));
        duration = `${Math.floor(mins / 60)}:${String(mins % 60).padStart(2, "0")}`;
      }

      const view = this._config.view || this.constructor.VIEW || "full";
      if (view !== "full") {
        this.shadowRoot.innerHTML = `
          <style>${CSS}</style>
          <ha-card class="${this._themeClass()} v-${view}" style="--led:${led.color}">
            ${this._staleBar(a, t)}
            ${this._renderView(view, { a, t, status, smart, led, power, name, isOnline, duration })}
          </ha-card>`;
        return;
      }

      this.shadowRoot.innerHTML = `
        <style>${CSS}</style>
        <ha-card class="${this._themeClass()}" style="--led:${led.color}">
          ${this._staleBar(a, t)}
          <header>
            <div class="title">
              <span class="name">${esc(name)}</span>
              <span class="model">${esc(a.model || "")}</span>
            </div>
            <span class="online ${isOnline ? "on" : "off"}" title="${isOnline ? "online" : "offline"}"></span>
          </header>
          ${this._modeBanner(a, t)}

          <section class="hero">
            <div class="post" aria-hidden="true" style="background-image:url('${CHARGER_IMG}')">
              <div class="strip ${led.anim}"><i></i></div>
            </div>
            <div class="readout">
              <div class="status">${esc(t.status[status] || status)}</div>
              <div class="power"><span class="big">${power !== null && status === "charging" ? this._num(power, 1) : "0"}</span><span class="unit">kW</span></div>
              <div class="smartline">${esc(t.smart[smart] || "")}</div>
              <dl class="facts">
                <div><dt>${t.session}</dt><dd>${this._num(a.session && a.session.energy, 1)} ${t.kwh}</dd></div>
                <div><dt>${t.cost}</dt><dd>${this._money(a.session && a.session.cost, a.currency)}</dd></div>
                <div><dt>${t.duration}</dt><dd>${duration}</dd></div>
              </dl>
            </div>
          </section>
          ${this._carRow(a, t)}
          ${this._eqRow(a, t)}

          <div class="modes" role="radiogroup">
            ${["normal", "smart", "solar", "solar_smart"]
              .filter((m) => a.has_surplus_source || !m.startsWith("solar"))
              .map((m) => `<button class="mode m-${m} ${a.mode === m ? "sel" : ""}" data-act="mode" data-mode="${m}" role="radio" aria-checked="${a.mode === m}">${t.modes[m]}</button>`)
              .join("")}
          </div>
          ${String(a.mode || "").startsWith("solar") ? this._solarStrip(a, t) : ""}

          <nav class="tabs">
            ${tabs
              .filter((x) => x !== "grid" || (a.equalizer && Object.keys(a.equalizer).length) || a.has_surplus_source)
              .map((x) => `<button class="tab ${this._tab === x ? "sel" : ""}" data-act="tab" data-tab="${x}">${x === "grid" && !(a.equalizer && Object.keys(a.equalizer).length) ? t.tabs.meter : t.tabs[x]}</button>`)
              .join("")}
          </nav>
          <section class="body">${body()}</section>
        </ha-card>`;
    }

    _themeClass() {
      const theme = (this._config && this._config.theme) || "auto";
      if (theme === "dark" || theme === "light") return theme;
      const dark = this._hass && this._hass.themes && this._hass.themes.darkMode;
      return dark === false ? "light" : "dark";
    }

    // Home Assistant's service worker can hand out an older copy of this file (e.g. right
    // after a restart). The integration reports its version, so we can say so.
    _staleBar(a, t) {
      if (!a || !a.card_version || a.card_version === VERSION) return "";
      return `<div class="stale"><span>${t.stale}</span><button data-act="reload">${t.reload}</button></div>`;
    }

    _section(title) {
      return title ? `<div class="sectitle">${esc(title)}</div>` : "";
    }

    _renderView(view, c) {
      const { a, t } = c;
      const title = this._config.title;
      switch (view) {
        case "charger": return this._viewCharger(c);
        case "modes": return this._section(title) + this._viewModes(c);
        case "cars": return this._section(title || t.carsTitle) + this._viewCars(a, t);
        case "plan": return this._section(title || t.tabs.plan) + this._tabPlan(a, t);
        case "grid": return this._section(title || (a.equalizer && Object.keys(a.equalizer).length ? t.tabs.grid : t.tabs.meter)) + this._tabGrid(a, t);
        case "costs": return this._section(title || t.tabs.history) + this._tabHistory(a, t);
        case "equalizer": return this._section(title) + this._viewEqualizer(a, t);
        default: return "";
      }
    }

    _viewCharger({ a, t, status, smart, led, power, name }) {
      const kw = power !== null && status === "charging" ? this._num(power, 1) : this._num(0, 1);
      const solarOn = String(a.mode || "").startsWith("solar") && a.surplus_kw !== null && a.surplus_kw !== undefined;
      const top = solarOn
        ? `☀ ${t.surplus}: ${this._num(Math.max(0, Number(a.surplus_kw) || 0), 2)} kW`
        : a.ere ? `${t.ere} ${t.month.toLowerCase()}: ${this._money(a.ere.month, a.currency)}` : `${t.today}: ${this._money(a.today && a.today.cost, a.currency)}`;
      const car = a.car;
      const statusText = CONNECTED.has(status) ? (car ? `${car.name}${car.soc !== null && car.soc !== undefined ? " · " + this._num(car.soc, 0) + "%" : ""}` : t.status[status] || status) : t.status[status] || status;
      return `
        <div class="bighead"><b>${esc(name)}</b><span>${esc(a.model || "")} · ${esc(t.smart[smart] || "")}</span></div>
        ${this._modeBanner(a, t)}
        <div class="bigpost" style="background-image:url('${CHARGER_IMG}')">
          <span class="pill ptop ${solarOn ? "sun" : ""}">${top}</span>
          <div class="bigkw">${kw}<small> kW</small></div>
          <div class="strip big ${led.anim}"><i></i></div>
          <span class="pill pstatus"><i class="dot"></i>${esc(statusText)}</span>
          <span class="pill pprice">${t.priceNow}: ${this._money(a.price, a.currency).replace(/(\d)$/, "$1")}/kWh</span>
        </div>`;
    }

    _viewModes({ a, t, status }) {
      const charging = status === "charging";
      const canStart = CONNECTED.has(status) && !charging && status !== "completed";
      const icons = {
        normal: '<path d="M7 2v11h3v9l7-12h-4l4-8z"/>',
        smart: '<path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8z"/>',
        solar: '<path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM2 13h2a1 1 0 0 0 0-2H2a1 1 0 0 0 0 2zm18 0h2a1 1 0 0 0 0-2h-2a1 1 0 0 0 0 2zM11 2v2a1 1 0 0 0 2 0V2a1 1 0 0 0-2 0zm0 18v2a1 1 0 0 0 2 0v-2a1 1 0 0 0-2 0zM5.99 4.58a1 1 0 0 0-1.41 1.41l1.06 1.06a1 1 0 0 0 1.41-1.41L5.99 4.58zm12.37 12.37a1 1 0 0 0-1.41 1.41l1.06 1.06a1 1 0 0 0 1.41-1.41l-1.06-1.06zm1.06-10.96a1 1 0 0 0-1.41-1.41l-1.06 1.06a1 1 0 0 0 1.41 1.41l1.06-1.06zM7.05 18.36a1 1 0 0 0-1.41-1.41l-1.06 1.06a1 1 0 0 0 1.41 1.41l1.06-1.06z"/>',
        solar_smart: '<path d="M12 7a5 5 0 1 0 5 5h-5V7zM2 13h2a1 1 0 0 0 0-2H2a1 1 0 0 0 0 2zM11 2v2a1 1 0 0 0 2 0V2a1 1 0 0 0-2 0zm0 18v2a1 1 0 0 0 2 0v-2a1 1 0 0 0-2 0zM14 9h8l-4 6h-4z"/>',
      };
      const modes = ["normal", "smart", "solar", "solar_smart"].filter((m) => a.has_surplus_source || !m.startsWith("solar"));
      return `
        ${this._config.mode_banner === true ? this._modeBanner(a, t) : ""}
        <div class="bigmodes" style="grid-template-columns:repeat(${modes.length},1fr)">
          ${modes.map((m) => `<button class="bigmode m-${m} ${a.mode === m ? "sel" : ""}" data-act="mode" data-mode="${m}"><svg viewBox="0 0 24 24">${icons[m]}</svg><span>${t.modes[m]}</span></button>`).join("")}
        </div>
        <div class="actions">
          <button class="act primary" data-act="${charging ? "pause" : "resume"}" ${charging || canStart ? "" : "disabled"}>${charging ? t.pause : t.resume}</button>
          <button class="act ${a.boost ? "on" : ""}" data-act="boost" ${CONNECTED.has(status) ? "" : "disabled"}>${t.boost}</button>
        </div>
        ${this._solarStrip(a, t)}
        <p class="note">${esc(t.smart[a.smart_state] || "")}</p>`;
    }

    _solarStrip(a, t) {
      if (!a.has_surplus_source || a.surplus_kw === null || a.surplus_kw === undefined) return "";
      const kw = Math.max(0, Number(a.surplus_kw) || 0);
      const need = Number(a.solar_start_kw) || 0;
      const pct = need > 0 ? Math.min(100, (kw / need) * 100) : 0;
      const active = String(a.mode || "").startsWith("solar");
      return `
        <div class="solar ${active ? "on" : ""} ${kw >= need && need > 0 ? "ok" : ""}">
          <div class="srow"><svg viewBox="0 0 24 24"><path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM11 1h2v3h-2zm0 19h2v3h-2zM1 11h3v2H1zm19 0h3v2h-3zM4.2 5.6l1.4-1.4 2.1 2.1-1.4 1.4zm12.1 12.1 1.4-1.4 2.1 2.1-1.4 1.4zM4.2 18.4l2.1-2.1 1.4 1.4-2.1 2.1zM16.3 6.3l2.1-2.1 1.4 1.4-2.1 2.1z"/></svg>
            <span>${kw > 0.05 ? t.solarAvail : t.solarNone}</span><b>${this._num(kw, 2)} kW</b></div>
          <div class="sbar"><i style="width:${pct.toFixed(0)}%"></i></div>
          <div class="sfoot">${t.solarStart} ${this._num(need, 1)} kW</div>
        </div>`;
    }

    _viewCars(a, t) {
      const cars = a.cars_detail || [];
      if (!cars.length) return `<p class="note">${t.noCars}</p>`;
      const active = a.car && a.car.name;
      return `<div class="cars">${cars.map((c) => {
        const soc = c.soc === null || c.soc === undefined ? null : Number(c.soc);
        const img = c.image ? `<img src="${esc(c.image)}" alt="" loading="lazy">` : `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/></svg>`;
        return `
          <button class="cartile ${c.name === active ? "active" : ""}" data-act="car" data-name="${esc(c.name)}">
            <div class="cimg">${img}<span class="chip ${c.plugged ? "on" : ""}"><i class="dot"></i>${soc === null ? "–" : this._num(soc, 0) + "%"}</span></div>
            <div class="chead"><b>${esc(c.name)}</b><span>${this._num(c.capacity, 0)} kWh</span></div>
            <div class="socbar"><i style="width:${soc === null ? 0 : Math.max(0, Math.min(100, soc))}%"></i><em style="left:${Math.min(100, Number(c.target || 0))}%"></em></div>
            <div class="cfoot">${c.plugged ? t.pluggedIn : t.notPlugged}${c.range_km ? ` · ${this._num(c.range_km, 0)} km` : ""} · ${t.target} ${this._num(c.target, 0)}%</div>
          </button>`;
      }).join("")}</div>`;
    }

    _carRow(a, t) {
      const car = a.car;
      if (!car) return "";
      const soc = car.soc === null || car.soc === undefined ? null : Number(car.soc);
      const pct = soc === null ? 0 : Math.max(0, Math.min(100, soc));
      const target = Number(car.target || 0);
      const img = car.image
        ? `<img class="carimg" src="${esc(car.image)}" alt="" loading="lazy">`
        : `<div class="carimg placeholder" aria-hidden="true"><svg viewBox="0 0 24 24"><path fill="currentColor" d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/></svg></div>`;
      return `
        <div class="car">
          ${img}
          <div class="carinfo">
            <div class="carhead"><b>${esc(car.name)}</b><span>${soc === null ? "–" : this._num(soc, 0) + "%"} → ${this._num(target, 0)}%${car.range_km ? ` · ${this._num(car.range_km, 0)} km` : ""}</span></div>
            <div class="socbar"><i style="width:${pct}%"></i><em style="left:${Math.min(100, target)}%"></em></div>
          </div>
          ${car.can_refresh ? `<button class="iconbtn" data-act="refresh" title="${t.refresh}" aria-label="${t.refresh}"><svg viewBox="0 0 24 24"><path fill="currentColor" d="M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg></button>` : ""}
        </div>`;
    }

    _modeBanner(a, t) {
      const m = a.boost ? "boost" : a.mode || "normal";
      const label = a.boost ? t.boost : t.modes[m] || m;
      const desc = a.boost ? "" : (t.modeDesc && t.modeDesc[m]) || "";
      const ph = Number(a.active_phases || a.phases || 3);
      const phase = Number(a.phases) === 3 || ph === 1 ? `<span class="mbphase">${ph === 1 ? t.phase1 : t.phase3}</span>` : "";
      return `
        <div class="modebanner mb-${m}">
          <span class="mbdot"></span>
          <div class="mbtext"><b>${t.modeNow}: ${esc(label)}</b>${desc ? `<span>${esc(desc)}</span>` : ""}</div>
          ${phase}
        </div>`;
    }

    _eqShown(a) {
      return !!(a.equalizer_info && a.equalizer_info.show);
    }

    _eqOnline(a) {
      const st = this._state((a.equalizer || {}).online);
      return st ? st.state === "on" : null;
    }

    _eqRow(a, t) {
      if (!this._eqShown(a)) return "";
      const info = a.equalizer_info || {};
      const grid = a.grid_power_kw;
      const online = this._eqOnline(a);
      const fuse = a.main_fuse;
      const bars = (a.phase_currents || []).map((c) => {
        const pct = fuse && c !== null && c !== undefined ? Math.min(100, (c / fuse) * 100) : 0;
        return `<i class="${pct > 90 ? "hot" : pct > 70 ? "warm" : ""}" style="height:${Math.max(8, pct).toFixed(0)}%"></i>`;
      }).join("");
      const flow = grid === null || grid === undefined ? "–"
        : `${grid < 0 ? t.exporting : t.importing} ${this._num(Math.abs(grid), 2)} kW`;
      return `
        <button class="eqrow" data-act="tab" data-tab="grid" title="${esc(info.name || t.eqTitle)}">
          <img class="eqimg" src="${EQ_IMG}" alt="" loading="lazy">
          <div class="eqinfo">
            <div class="eqhead"><b>${esc(info.name || t.eqTitle)}</b>${online === null ? "" : `<span class="online ${online ? "on" : "off"}"></span>`}</div>
            <span>${info.linked === false ? t.eqNone : `${flow}${a.phase_load_pct !== null && a.phase_load_pct !== undefined ? ` · ${this._num(a.phase_load_pct, 0)}% ${t.eqLoad}` : ""}`}</span>
          </div>
          ${bars ? `<div class="eqbars" aria-hidden="true">${bars}</div>` : ""}
        </button>`;
    }

    _viewEqualizer(a, t) {
      const info = a.equalizer_info || {};
      const eq = a.equalizer || {};
      if (!info.linked) return `<p class="note">${t.eqNone}</p>`;
      const online = this._eqOnline(a);
      const grid = a.grid_power_kw;
      const exporting = grid !== null && grid !== undefined && grid < 0;
      const fuse = a.main_fuse;
      const phases = (a.phase_currents || []).map((c, i) => {
        const pct = fuse && c !== null && c !== undefined ? Math.min(100, (c / fuse) * 100) : 0;
        const warn = pct > 90 ? "hot" : pct > 70 ? "warm" : "";
        return `<div class="phase">
            <span>L${i + 1}</span>
            <div class="track"><i class="${warn}" style="width:${pct.toFixed(0)}%"></i></div>
            <b>${this._num(c, 1)} A</b>
            <small>${this._num(a.phase_voltages && a.phase_voltages[i], 0)} V</small>
          </div>`;
      }).join("");
      const imp = this._val(eq.import_energy), exp = this._val(eq.export_energy);
      const limit = this._val(eq.max_continuous_limit);
      const temp = this._val(eq.temp_max);
      return `
        <div class="eqhero">
          <img src="${EQ_IMG}" alt="">
          <div class="eqmeta">
            <b>${esc(info.name || t.eqTitle)}</b>
            <span>${esc(info.model || "Equalizer")}${info.sw_version ? ` · ${t.eqFirmware} ${esc(info.sw_version)}` : ""}</span>
            ${online === null ? "" : `<span class="state ${online ? "ok" : "bad"}"><i class="dot"></i>${online ? t.eqOnline : t.eqOffline}</span>`}
            <div class="eqkw ${exporting ? "out" : "in"}">${grid === null || grid === undefined ? "–" : this._num(Math.abs(grid), 2)}<small> kW</small></div>
            <span class="eqdir">${grid === null || grid === undefined ? "" : exporting ? t.exporting : t.importing}</span>
          </div>
        </div>
        <div class="grid3">
          <div class="tile"><span>${t.surplus}</span><b>${this._num(Math.max(0, Number(a.surplus_kw) || 0), 2)} kW</b><small>${t.now}</small></div>
          <div class="tile"><span>${t.fuse}</span><b>${this._num(fuse, 0)} A</b><small>${a.phase_headroom !== null && a.phase_headroom !== undefined ? `${this._num(a.phase_headroom, 1)} A ${t.headroom}` : "&nbsp;"}</small></div>
          <div class="tile"><span>${t.eqLoadT}</span><b>${this._num(a.phase_load_pct, 0)}%</b><small>${t.eqPhases}</small></div>
        </div>
        ${(a.phase_currents || []).some((c) => c !== null && c !== undefined) ? `<div class="phases eqphases">${phases}</div>` : ""}
        <div class="sectitle eqsub">${t.eqTotals}</div>
        <div class="grid3">
          <div class="tile"><span>${t.importing}</span><b>${this._num(imp, 0)}</b><small>${t.kwh}</small></div>
          <div class="tile"><span>${t.exporting}</span><b>${this._num(exp, 0)}</b><small>${t.kwh}</small></div>
          <div class="tile"><span>${limit !== null ? t.eqLimit : t.eqTemp}</span><b>${limit !== null ? this._num(limit, 0) + " A" : this._num(temp, 0) + " °C"}</b><small>${limit !== null && temp !== null ? `${this._num(temp, 0)} °C` : "Equalizer"}</small></div>
        </div>`;
    }

    _tabCharge(a, t, status) {
      const src = a.sources || {};
      const lockSw = this._state(src.cable_locked_permanently);
      const locked = lockSw && lockSw.state === "on";
      const charging = status === "charging";
      const canStart = CONNECTED.has(status) && !charging && status !== "completed";
      const limit = this._val(src.dynamic_charger_limit);
      const current = this._val(src.current);
      const reason = this._state(src.reason_for_no_current);
      return `
        <div class="actions">
          <button class="act primary" data-act="${charging ? "pause" : "resume"}" ${charging || canStart ? "" : "disabled"}>
            ${charging ? t.pause : t.resume}
          </button>
          <button class="act ${a.boost ? "on" : ""}" data-act="boost" ${CONNECTED.has(status) ? "" : "disabled"}>${t.boost}</button>
          ${lockSw ? `<button class="act ${locked ? "on" : ""}" data-act="lock">${locked ? t.lock : t.unlock}</button>` : ""}
        </div>
        <div class="grid3">
          <div class="tile"><span>${t.today}</span><b>${this._num(a.today && a.today.energy, 1)} ${t.kwh}</b><small>${this._money(a.today && a.today.cost, a.currency)}</small></div>
          <div class="tile"><span>${t.amps}</span><b>${this._num(current, 1)} A</b><small>max ${this._num(limit, 0)} A</small></div>
          <div class="tile"><span>${a.currency || "€"}/kWh</span><b>${this._num(a.price, 3)}</b><small>${t.now}</small></div>
        </div>
        ${reason && !/^\(?0\)?\b|No reason/i.test(reason.state) && CONNECTED.has(status) ? `<p class="note">${esc(reason.state)}</p>` : ""}`;
    }

    _tabPlan(a, t) {
      const ent = a.entities || {};
      const useSoc = a.has_soc && ent.target_soc && !a.manual_kwh;
      const targetVal = useSoc ? a.target_soc : a.target_energy;
      const step = useSoc ? 5 : 1;
      const unit = useSoc ? "%" : t.kwh;
      const chart = this._priceChart(a, t);
      const pm = a.boost ? "boost" : a.mode || "normal";
      const noPlanMode = pm === "normal" || pm === "boost" || pm === "solar";
      const dur = (h) => { const m = Math.round(h * 60); return m >= 60 ? `${Math.floor(m / 60)} u ${String(m % 60).padStart(2, "0")} min`.replace(" u ", this._lang.startsWith("en") ? " h " : this._lang.startsWith("de") ? " Std. " : " u ") : `${m} min`; };
      const short = !noPlanMode && a.plan_short_kwh > 0.05 && a.charge_power_kw
        ? `<p class="note warn">${t.tooShort.replace("{dep}", esc(a.departure || "")).replace("{kw}", this._num(a.charge_power_kw, 1)).replace("{fit}", this._num(a.plan_window_kwh, 1))
            .replace("{need}", this._num(a.energy_needed, 1)).replace("{dur}", dur((a.energy_needed || 0) / a.charge_power_kw))}</p>` : "";
      const summary = (noPlanMode ? ""
        : !a.prices || !a.prices.length ? `<p class="note">${a.smart_state === "no_prices" && a.no_prices_action === "wait" ? t.noPricesWait : t.noPrices}</p>`
        : a.plan && a.plan.length
        ? `${a.plan_preview ? `<p class="note preview">${t.preview}</p>` : ""}<div class="plansum ${a.plan_preview ? "preview" : ""}">
             <div><span>${t.planStart}</span><b>${this._time(a.next_start)}</b></div>
             <div><span>${t.planEnd}</span><b>${this._time(a.complete_by)}</b></div>
             <div><span>${t.planCost}</span><b>${this._money(a.plan_cost, a.currency)}</b></div>
           </div>`
        : `<p class="note">${a.prices && a.prices.length ? t.noPlan : t.noPrices}</p>`);
      return `
        <div class="controls">
          <label class="ctl"><span>${t.departure}</span>
            <input type="time" value="${esc(a.departure || "07:00")}" data-ctl="departure">
          </label>
          <div class="ctl"><span class="ctlhead">${useSoc ? t.targetSoc : t.target}${a.has_soc && ent.manual_kwh ? `<span class="unitsw" role="group">
                <button data-act="tgtype" data-kwh="0" class="${useSoc ? "on" : ""}" title="${t.byPct}" aria-label="${t.byPct}">${t.unitPct}</button><button data-act="tgtype" data-kwh="1" class="${useSoc ? "" : "on"}" title="${t.byKwh}" aria-label="${t.byKwh}">${t.unitKwh}</button></span>` : ""}</span>
            <div class="stepper">
              <button data-act="step" data-dir="-1" data-step="${step}" aria-label="−">−</button>
              <b>${this._num(targetVal, 0)} ${unit}</b>
              <button data-act="step" data-dir="1" data-step="${step}" aria-label="+">+</button>
            </div>
          </div>
          <div class="ctl"><span>${t.needed}</span><b class="plain">${this._num(a.energy_needed, 1)} ${t.kwh}</b></div>
        </div>
        ${short}
        ${chart}
        ${this._solarSummary(a, t)}
        ${summary}`;
    }

    _priceChart(a, t) {
      const day = Number(this._chartDay) || 0;                       // -1 yesterday, 0 now, 1 tomorrow
      const now = Date.now();
      const midnight = new Date(); midnight.setHours(0, 0, 0, 0);
      const Q = 900e3;
      let from, to;
      if (day === 0) { from = Math.floor((now - 6 * 3600e3) / Q) * Q; to = from + 30 * 3600e3; }
      else { from = midnight.getTime() + day * 86400e3; to = from + 86400e3; }
      // time grid (quarter hours); prices are looked up per slot (works for hourly prices too)
      const priceList = (a.prices || []).map((p) => ({ s: new Date(p.start).getTime(), e: new Date(p.end).getTime(), p }));
      const priceAt = (ms) => { const x = priceList.find((q) => q.s <= ms && ms < q.e); return x ? x.p : null; };
      const grid = [];
      for (let ms = from; ms < to; ms += Q) grid.push({ s: ms, e: ms + Q, price: priceAt(ms) });
      const withPrice = grid.filter((g) => g.price);
      const solar = a.solar || null;
      const pvHourly = new Map(((solar && solar.pv_hourly) || []).map((x) => [new Date(x.start).getTime(), x.kw]));
      const pvAt = (ms) => pvHourly.get(Math.floor(ms / 3600e3) * 3600e3);
      const hist = new Map((a.history || []).map((x) => [new Date(x.start).getTime(), x]));
      const sched = new Map((a.schedule || []).map((x) => [new Date(x.start).getTime(), x]));
      const hasPv = grid.some((g) => pvAt(g.s) !== undefined);
      if (!withPrice.length && !hasPv && !hist.size) return this._dayNav(t, day) + `<p class="note">${t.noPrices}</p>`;

      const mode = a.boost ? "boost" : a.mode || "normal";
      const always = mode === "normal" || mode === "boost";
      const onlySun = mode === "solar";
      const sunNow = a.smart_state === "charging_solar";
      const inPlan = (g) => (a.plan || []).some((x) => new Date(x.start).getTime() < g.e && new Date(x.end).getTime() > g.s);
      const vals = withPrice.map((g) => g.price.price);
      const max = vals.length ? Math.max(...vals, 0.01) : 0.3;
      const lo = vals.length ? Math.min(...vals) : 0;
      const min = lo < 0 ? lo : Math.max(0, lo - (max - lo) * 0.35);
      const W = 600, H = 120, pad = 1.2;
      const bw = W / grid.length;
      const y = (v) => H - ((v - min) / (max - min || 1)) * (H - 14) - 2;
      const zero = Math.max(0, Math.min(H, y(0)));
      let nowX = null;
      const bars = grid.map((g, i) => {
        if (now >= g.s && now < g.e) nowX = i * bw + ((now - g.s) / Q) * bw;
        if (!g.price) return "";
        const v = g.price.price;
        const top = Math.min(y(v), zero), h = Math.max(1.5, Math.abs(zero - y(v)));
        let cls = inPlan(g) ? (a.plan_preview ? "bar plan pv" : "bar plan") : "bar";
        if (always && g.e > now) cls = "bar plan";        // Normal: it charges at any price
        else if (onlySun) cls = "bar";                     // Solar: price plays no role
        if (now >= g.s && now < g.e && sunNow) cls = "bar sun";
        if (g.e <= now) cls = "bar past";                  // history: dimmer
        return `<rect class="${cls}" x="${(i * bw + pad / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${Math.max(0.8, bw - pad).toFixed(1)}" height="${h.toFixed(1)}" rx="1"><title>${this._time(g.price.start)} · ${this._num(v, 3)}</title></rect>`;
      }).join("");

      // sun: dashed = forecast, solid = what the panels really made (from the history)
      let pvMax = 0;
      grid.forEach((g) => { const f = pvAt(g.s); const r = hist.get(g.s); pvMax = Math.max(pvMax, f || 0, r && r.pv ? r.pv * 4 : 0); });
      pvMax = Math.max(0.5, pvMax);
      const yp = (v) => H - (Math.max(0, v) / pvMax) * (H - 18) - 2;
      const fPts = [], rPts = [];
      grid.forEach((g, i) => {
        const x = (i * bw + bw / 2).toFixed(1);
        const f = pvAt(g.s);
        if (f !== undefined) fPts.push(`${x},${yp(f).toFixed(1)}`);
        const r = hist.get(g.s);
        if (g.e <= now && r && r.pv !== undefined) rPts.push(`${x},${yp(r.pv * 4).toFixed(1)}`);
      });
      const sunLine = fPts.length > 1 ? `<polyline class="sunline" points="${fPts.join(" ")}"></polyline>` : "";
      const realLine = rPts.length > 1 ? `<polyline class="sunreal" points="${rPts.join(" ")}"></polyline>` : "";

      // strip: per quarter kWh from the grid (blue) and the sun (yellow); solid = charged, light = expected
      const S = 40, top0 = H + 3;
      const energies = grid.map((g) => {
        if (g.e <= now) { const h = hist.get(g.s); return { g: h ? h.grid : 0, u: h ? h.sun : 0, past: true }; }
        const x = sched.get(g.s);
        return { g: x ? x.grid : 0, u: x ? x.sun : 0, past: false };
      });
      const eMax = Math.max(0.25, ...energies.map((e) => e.g + e.u));
      const hasStrip = energies.some((e) => e.g + e.u > 0.001);
      const strip = hasStrip ? energies.map((e, i) => {
        if (e.g + e.u <= 0.001) return "";
        const x = (i * bw + pad / 2).toFixed(1), w = Math.max(0.8, bw - pad).toFixed(1);
        const hg = (e.g / eMax) * S, hu = (e.u / eMax) * S;
        const tip = `<title>${this._time(new Date(grid[i].s).toISOString())} · ${t.fromGrid} ${this._num(e.g, 2)} kWh · ☀ ${this._num(e.u, 2)} kWh${e.past ? "" : " (" + t.expected + ")"}</title>`;
        return `<g class="estrip${e.past ? "" : " plan"}">${hg > 0.2 ? `<rect class="eg" x="${x}" y="${top0}" width="${w}" height="${hg.toFixed(1)}" rx="1">${tip}</rect>` : ""}${hu > 0.2 ? `<rect class="eu" x="${x}" y="${(top0 + hg).toFixed(1)}" width="${w}" height="${hu.toFixed(1)}" rx="1">${tip}</rect>` : ""}</g>`;
      }).join("") : "";
      const tickY = hasStrip ? H + S + 16 : H + 14;
      const vbH = tickY + 6;
      // labels live in HTML on top of the svg: the svg is stretched (preserveAspectRatio none), text would be squeezed
      const lbl = (cls, x, y, txt, end) => `<span class="clbl ${cls}${end ? " end" : ""}" style="${end ? "right" : "left"}:${(end ? 100 - (x / W) * 100 : (x / W) * 100).toFixed(2)}%;top:${(((y + 4) / vbH) * 100).toFixed(2)}%">${txt}</span>`;
      const every = day === 0 ? 6 : 3;
      const ticks = grid.map((g, i) => {
        const d = new Date(g.s);
        return i > 0 && d.getMinutes() === 0 && d.getHours() % every === 0 ? lbl("tick", i * bw, tickY, `${String(d.getHours()).padStart(2, "0")}:00`) : "";
      }).join("");
      const legend = [
        withPrice.length ? (mode === "solar_smart" && day >= 0
          ? `<span><i class="key sun"></i>${t.sunFirst}</span><span><i class="key plan"></i>${t.cheapHours}</span>`
          : `<span><i class="key ${onlySun ? "sun" : "plan"}"></i>${onlySun ? t.modes.solar : always ? t.modes.normal : t.planned}</span>`) +
          `<span class="muted">${this._num(lo, 3)} – ${this._num(max, 3)} ${a.currency || "€"}/kWh</span>` : `<span class="muted">${day === 1 ? t.pricesLater : t.noPrices}</span>`,
        fPts.length > 1 ? `<span><i class="key dots"></i>${t.sunForecast}</span>` : "",
        rPts.length > 1 ? `<span><i class="key sunreal"></i>${t.sunReal}</span>` : "",
      ].join("");
      const note = day !== 0 ? "" : always ? t.chartNormal : onlySun ? t.chartSolar : mode === "solar_smart" ? t.chartSolarSmart : "";
      return `
        ${this._dayNav(t, day)}
        <figure class="chart${hasStrip ? " withstrip" : ""}">
          <div class="plot"><svg viewBox="0 -4 ${W} ${tickY + 6}" preserveAspectRatio="none" role="img">
            <line class="zero" x1="0" x2="${W}" y1="${zero.toFixed(1)}" y2="${zero.toFixed(1)}"></line>
            ${bars}
            ${sunLine}
            ${realLine}
                        ${hasStrip ? `<line class="zero" x1="0" x2="${W}" y1="${top0}" y2="${top0}"></line>${strip}` : ""}
            ${nowX !== null ? `<line class="nowline" x1="${nowX.toFixed(1)}" x2="${nowX.toFixed(1)}" y1="0" y2="${hasStrip ? top0 + S : H}"></line>` : ""}
          </svg>
          ${ticks}
          ${fPts.length > 1 || rPts.length > 1 ? lbl("sunmax", W - 2, 8, `☀ ${this._num(pvMax, 1)} kW`, true) : ""}
          ${hasStrip ? lbl("smax", W - 2, top0 + S - 2, `${this._num(eMax, 1)} kWh`, true) : ""}
          </div>
          <figcaption class="legend">${legend}</figcaption>
          ${hasStrip ? `<p class="stripkey"><span>↓ ${t.perQuarter}:</span><span><i class="key eg"></i>${t.fromGrid}</span><span><i class="key eu"></i>${t.fromSun}</span><span class="muted">${t.solidLight}</span></p>` : ""}
          ${note ? `<p class="note chartnote">${note}</p>` : ""}
        </figure>`;
    }

    _dayNav(t, day) {
      const label = day === -1 ? t.yesterday : day === 1 ? t.tomorrowCap : t.nowCap;
      return `
        <div class="daynav">
          <button class="navbtn" data-act="day" data-dir="-1" ${day <= -1 ? "disabled" : ""} aria-label="${t.yesterday}">‹</button>
          <span>${label}</span>
          <button class="navbtn" data-act="day" data-dir="1" ${day >= 1 ? "disabled" : ""} aria-label="${t.tomorrowCap}">›</button>
        </div>`;
    }

    _solarSummary(a, t) {
      const sol = a.solar;
      if (!sol) return "";
      const mode = a.boost ? "boost" : a.mode || "normal";
      const time = sol.departure ? this._time(sol.departure) : "";
      const fill = (txt) => txt.replace("{sun}", this._num(sol.until_departure_kwh, 1)).replace("{grid}", this._num(sol.grid_kwh, 1)).replace("{time}", time);
      let line = "";
      if (mode === "solar_smart") line = sol.grid_kwh > 0.05 ? fill(t.planSun) : fill(t.planSunOnly);
      else if (mode === "solar") line = fill(t.planSolarOnly);
      const learning = sol.calibration && !sol.calibration.calibration_days;
      return `
        <div class="sunsum">
          <div class="tile"><span>${t.sunToday}</span><b>${this._num(sol.today_kwh, 1)} ${t.kwh}</b><small>${t.tomorrowShort} ${this._num(sol.tomorrow_kwh, 1)} ${t.kwh}</small></div>
          <div class="tile"><span>${t.sunUntil}</span><b>${this._num(sol.until_departure_kwh, 1)} ${t.kwh}</b><small>${t.chargeable}</small></div>
          <div class="tile"><span>${t.fromGrid}</span><b>${this._num(mode === "solar" ? 0 : sol.grid_kwh, 1)} ${t.kwh}</b><small>${mode === "normal" || mode === "boost" ? t.modes.normal : "&nbsp;"}</small></div>
        </div>
        ${line ? `<p class="note sunline-note"><b>${t.whatWillHappen}:</b> ${esc(line)}</p>` : ""}
        ${learning ? `<p class="note">${t.forecastLearning}</p>` : ""}`;
    }

    _tabGrid(a, t) {
      const eq = a.equalizer || {};
      const fuse = a.main_fuse;
      const grid = a.grid_power_kw;
      if (grid === null || grid === undefined) return `<p class="note">${t.noGrid}</p>`;
      const exporting = grid < 0;
      const phases = (a.phase_currents || []).map((c, i) => {
        const pct = fuse && c !== null ? Math.min(100, (c / fuse) * 100) : 0;
        const warn = pct > 90 ? "hot" : pct > 70 ? "warm" : "";
        return `<div class="phase">
            <span>L${i + 1}</span>
            <div class="track"><i class="${warn}" style="width:${pct.toFixed(0)}%"></i></div>
            <b>${this._num(c, 1)} A</b>
            <small>${this._num(a.phase_voltages && a.phase_voltages[i], 0)} V</small>
          </div>`;
      }).join("");
      const hasPhases = (a.phase_currents || []).some((c) => c !== null);
      const imp = this._val(eq.import_energy), exp = this._val(eq.export_energy);
      return `
        <div class="flow ${exporting ? "out" : "in"}">
          <div><span>${exporting ? t.exporting : t.importing}</span><b>${this._num(Math.abs(grid), 2)} kW</b></div>
          ${a.surplus_kw !== null && a.surplus_kw !== undefined ? `<div><span>${t.surplus}</span><b>${this._num(Math.max(0, a.surplus_kw), 2)} kW</b></div>` : ""}
          ${fuse ? `<div><span>${t.fuse}</span><b>${this._num(fuse, 0)} A</b>${a.phase_headroom !== null && a.phase_headroom !== undefined ? `<small>${this._num(a.phase_headroom, 1)} A ${t.headroom}</small>` : ""}</div>` : ""}
        </div>
        ${hasPhases ? `<div class="phases">${phases}</div>` : ""}
        ${imp !== null || exp !== null ? `<div class="grid3">
            <div class="tile"><span>${t.importing}</span><b>${this._num(imp, 0)}</b><small>${t.kwh}</small></div>
            <div class="tile"><span>${t.exporting}</span><b>${this._num(exp, 0)}</b><small>${t.kwh}</small></div>
            <div class="tile"><span>°C</span><b>${this._num(this._val(eq.temp_max), 0)}</b><small>Equalizer</small></div>
          </div>` : ""}`;
    }

    _tabHistory(a, t) {
      const m = a.month || {};
      const avg = m.energy ? m.cost / m.energy : null;
      const months = (a.months || []).slice(-6);
      const maxE = Math.max(...months.map((x) => x.energy), 1);
      const sessions = (a.sessions || []).slice(0, 8);
      return `
        <div class="grid3">
          <div class="tile"><span>${t.month}</span><b>${this._num(m.energy, 1)} ${t.kwh}</b><small>${this._money(m.cost, a.currency)}</small></div>
          <div class="tile"><span>${t.avg} ${a.currency || "€"}/kWh</span><b>${this._num(avg, 3)}</b><small>${t.month.toLowerCase()}</small></div>
          ${a.reimbursement_per_kwh !== null && a.reimbursement_per_kwh !== undefined
            ? `<div class="tile"><span>${t.reimb}</span><b>${this._money((m.energy || 0) * a.reimbursement_per_kwh, a.currency)}</b><small>${this._num(a.reimbursement_per_kwh, 3)}/${t.kwh}</small></div>`
            : `<div class="tile"><span>${t.today}</span><b>${this._num(a.today && a.today.energy, 1)} ${t.kwh}</b><small>${this._money(a.today && a.today.cost, a.currency)}</small></div>`}
        </div>
        ${a.ere ? `<div class="grid3 ere">
            <div class="tile"><span>${t.ere} ${t.month.toLowerCase()}</span><b>${this._money(a.ere.month, a.currency)}</b><small>${this._num(a.ere.rate, 3)}/${t.kwh}</small></div>
            <div class="tile"><span>${t.ere} ${t.year.toLowerCase()}</span><b>${this._money(a.ere.year, a.currency)}</b><small>&nbsp;</small></div>
            <div class="tile"><span>${t.ere} ${t.total.toLowerCase()}</span><b>${this._money(a.ere.total, a.currency)}</b><small>&nbsp;</small></div>
          </div>` : ""}
        ${months.length > 1 ? `<div class="months">${months.map((x) => `
            <div class="mcol" title="${esc(x.month)}: ${this._num(x.energy, 1)} kWh · ${this._money(x.cost, a.currency)}">
              <i style="height:${Math.max(4, (x.energy / maxE) * 100).toFixed(0)}%"></i>
              <span>${new Date(x.month + "-01").toLocaleDateString(this._lang, { month: "short" })}</span>
            </div>`).join("")}</div>` : ""}
        <h4>${t.sessions}</h4>
        ${sessions.length ? `<ul class="sessions">${sessions.map((s) => `
            <li><span>${this._day(s.start)} ${this._time(s.start)}–${this._time(s.end)}</span>
            <b>${this._num(s.energy, 1)} ${t.kwh}</b><em>${this._money(s.cost, a.currency)}</em></li>`).join("")}</ul>` : `<p class="note">${t.none}</p>`}
        <button class="act wide" data-act="export">${this._exported ? t.exported : t.export}</button>`;
    }

    // ----------------------------------------------------------------- actions
    _attrs() {
      const st = this._hass.states[this._entityId()];
      return st ? st.attributes : {};
    }

    async _onClick(e) {
      const btn = e.target.closest("[data-act]");
      if (!btn || btn.disabled) return;
      const a = this._attrs();
      const ent = a.entities || {};
      const src = a.sources || {};
      const call = (d, s, data) => this._hass.callService(d, s, data);
      switch (btn.dataset.act) {
        case "tab":
          this._tab = btn.dataset.tab;
          this._sig = null;
          this._render();
          return;
        case "mode":
          if (ent.charge_mode) await call("select", "select_option", { entity_id: ent.charge_mode, option: btn.dataset.mode });
          return;
        case "pause":
        case "resume": {
          const status = this._hass.states[this._entityId()].state;
          const cmd = btn.dataset.act === "pause" ? "pause" : status === "awaiting_start" || status === "ready_to_charge" ? "resume" : "start";
          await call("easee", "action_command", { device_id: a.device_id, action_command: cmd });
          return;
        }
        case "tgtype":
          if (ent.manual_kwh) await call("switch", btn.dataset.kwh === "1" ? "turn_on" : "turn_off", { entity_id: ent.manual_kwh });
          return;
        case "boost":
          if (ent.boost) await call("switch", a.boost ? "turn_off" : "turn_on", { entity_id: ent.boost });
          return;
        case "lock": {
          const sw = this._hass.states[src.cable_locked_permanently];
          if (sw) await call("switch", sw.state === "on" ? "turn_off" : "turn_on", { entity_id: src.cable_locked_permanently });
          return;
        }
        case "step": {
          const useSoc = a.has_soc && ent.target_soc && !a.manual_kwh;
          const id = useSoc ? ent.target_soc : ent.target_energy;
          const cur = useSoc ? a.target_soc : a.target_energy;
          const next = Math.min(useSoc ? 100 : 120, Math.max(useSoc ? 10 : 1, Number(cur) + Number(btn.dataset.dir) * Number(btn.dataset.step)));
          if (id) await call("number", "set_value", { entity_id: id, value: next });
          return;
        }
        case "car":
          if (ent.active_car) await call("select", "select_option", { entity_id: ent.active_car, option: btn.dataset.name });
          return;
        case "reload":
          location.reload();
          return;
        case "day":
          this._chartDay = Math.max(-1, Math.min(1, (Number(this._chartDay) || 0) + Number(btn.dataset.dir)));
          this._sig = null;
          this._render();
          return;
        case "refresh":
          if (ent.refresh_car) await call("button", "press", { entity_id: ent.refresh_car });
          return;
        case "export": {
          // The CSV comes back in the action response and is saved by the browser;
          // nothing is written to /config/www (that folder is public).
          const a = this._attrs();
          const res = await this._hass.callService(
            "easee_smart", "export_report", a.entry_id ? { config_entry_id: a.entry_id } : {},
            undefined, true, true,
          );
          const r = (res && res.response) || {};
          if (r.csv) {
            const blob = new Blob(["\ufeff" + r.csv], { type: "text/csv;charset=utf-8" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = r.filename || "easee-smart.csv";
            document.body.appendChild(link);
            link.click();
            setTimeout(() => { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
          }
          this._exported = true;
          this._sig = null;
          this._render();
          return;
        }
        default:
      }
    }

    async _onChange(_e) {
      // saving happens in _onLeave
    }

    async _onLeave(e) {
      const el = e.target;
      if (!el || !el.dataset || el.dataset.ctl !== "departure") return;
      const a = this._attrs();
      const ent = a.entities || {};
      if (ent.departure_time && el.value && el.value !== (a.departure || "")) {
        await this._hass.callService("time", "set_value", { entity_id: ent.departure_time, time: `${el.value}:00` });
      }
      if (this._pending) { this._pending = false; this._sig = null; setTimeout(() => this._render(), 0); }
    }
  }

  const CSS = `
    :host { display:block; container-type:inline-size; }
    ha-card {
      display:block;
      --bg:#14181E; --panel:#1C2129; --line:#2A303A; --text:#EDF0F4; --muted:#8C95A2; --accent:#5AA9FF; --sun:#F5C542;
      background:var(--bg); color:var(--text); border-radius:var(--ha-card-border-radius,16px);
      padding:18px 18px 16px; font-family:var(--ha-font-family-body, "Roboto", system-ui, sans-serif);
      overflow:hidden; border:1px solid var(--line);
    }
    ha-card.light { --bg:#FFFFFF; --panel:#F2F4F7; --line:#E3E7EC; --text:#14181E; --muted:#6B7480; --accent:#2F7FE0; box-shadow:0 2px 10px rgba(20,24,30,.06); }
    ha-card.light .mode.sel, ha-card.light .bigmode.sel { background:#FFFFFF; box-shadow:0 1px 4px rgba(20,24,30,.12); }
    ha-card.light .bar { fill:#D5DAE1; }
    ha-card.light .nowline { stroke:#14181E; }
    ha-card.light .socbar { background:#E3E7EC; }
    ha-card.light .act.primary { color:#FFFFFF; }
    ha-card.light .mcol i { background:#D5DAE1; }
    .empty { padding:16px; color:var(--muted); }
    .modebanner { display:flex; align-items:center; gap:10px; background:var(--panel); border-radius:12px; padding:9px 12px; margin:0 0 12px; border-left:4px solid var(--mbc, var(--accent)); }
    .modebanner .mbdot { width:10px; height:10px; border-radius:50%; background:var(--mbc, var(--accent)); flex:none; box-shadow:0 0 0 4px color-mix(in srgb, var(--mbc, var(--accent)) 22%, transparent); }
    .modebanner .mbtext { flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }
    .modebanner .mbtext b { font-size:.9rem; font-weight:600; }
    .modebanner .mbtext span { font-size:.76rem; color:var(--muted); }
    .modebanner .mbphase { flex:none; font-size:.76rem; font-weight:600; padding:4px 9px; border-radius:999px; background:color-mix(in srgb, var(--mbc, var(--accent)) 18%, transparent); color:var(--mbc, var(--accent)); }
    .mb-normal { --mbc:#5AA9FF; } .mb-smart { --mbc:#3DDC84; } .mb-solar { --mbc:#F5C542; } .mb-solar_smart { --mbc:#F5C542; } .mb-boost { --mbc:#FF8A3D; }
    .stale { display:flex; align-items:center; gap:10px; background:rgba(90,169,255,.14); border:1px solid rgba(90,169,255,.4); color:var(--text); border-radius:12px; padding:8px 10px; margin:0 0 12px; font-size:.8rem; }
    .stale span { flex:1; }
    .stale button { background:var(--accent); color:#06121F; border:0; border-radius:8px; padding:6px 12px; font:inherit; font-weight:600; cursor:pointer; }
    .sectitle { font-size:.95rem; font-weight:600; margin:0 2px 12px; }

    /* big charger view */
    ha-card.v-charger { padding:14px 14px 22px; }
    .bighead { display:flex; flex-direction:column; gap:2px; margin:0 2px 10px; }
    .bighead b { font-size:1.15rem; font-weight:600; }
    .bighead span { font-size:.8rem; color:var(--muted); }
    .bigpost { position:relative; width:min(100%, 380px); margin:0 auto; aspect-ratio:301 / 405; background:center / contain no-repeat; container-type:inline-size; filter:drop-shadow(0 16px 22px rgba(0,0,0,.35)); }
    .bigkw { position:absolute; top:13%; left:0; right:0; text-align:center; color:#fff; font-size:13cqw; font-weight:600; letter-spacing:-.02em; line-height:1; text-shadow:0 2px 10px rgba(0,0,0,.35); font-variant-numeric:tabular-nums; }
    .bigkw small { font-size:.6em; font-weight:500; }
    .strip.big { width:1.6%; box-shadow:0 0 10px var(--led), 0 0 26px color-mix(in srgb, var(--led) 50%, transparent); }
    .pill { position:absolute; left:50%; transform:translateX(-50%); white-space:nowrap; font-size:3.6cqw; font-weight:600; padding:.55em 1.1em; border-radius:999px; background:#FFFFFF; color:#14181E; box-shadow:0 2px 8px rgba(0,0,0,.18); }
    .pill.ptop { top:1.5%; }
    .pill.pstatus { bottom:7.5%; background:#1C2129; color:#EDF0F4; display:flex; align-items:center; gap:.5em; }
    .pill.pprice { bottom:-3%; }
    .dot { width:.6em; height:.6em; border-radius:50%; background:var(--led); display:inline-block; }

    /* modes view */
    .bigmodes { display:grid; grid-template-columns:repeat(auto-fit, minmax(90px, 1fr)); gap:8px; margin-bottom:12px; }
    .bigmode { background:var(--panel); border:1px solid transparent; border-radius:14px; padding:14px 6px 12px; display:flex; flex-direction:column; align-items:center; gap:6px; color:var(--muted); font:inherit; font-size:.86rem; cursor:pointer; }
    .bigmode svg { width:22px; height:22px; fill:currentColor; }
    .bigmode.sel { color:var(--text); border-color:var(--accent); }
    .bigmode.sel svg { fill:var(--accent); }
    .bigmode.m-smart.sel { border-color:#3DDC84; } .bigmode.m-smart.sel svg { fill:#3DDC84; }
    .mode.m-smart.sel { color:#3DDC84; }
    .bigmode.m-solar.sel, .bigmode.m-solar_smart.sel { border-color:var(--sun); background:rgba(245,197,66,.10); }
    .bigmode.m-solar.sel svg, .bigmode.m-solar_smart.sel svg { fill:var(--sun); }
    .mode.m-solar.sel, .mode.m-solar_smart.sel { background:rgba(245,197,66,.18); color:var(--sun); }
    ha-card.light .mode.m-solar.sel, ha-card.light .mode.m-solar_smart.sel { color:#9A6B00; }
    .solar { background:var(--panel); border-radius:12px; padding:10px 12px; margin-top:10px; border:1px solid transparent; }
    .solar.on { border-color:rgba(245,197,66,.45); }
    .solar .srow { display:flex; align-items:center; gap:8px; font-size:.86rem; color:var(--muted); }
    .solar .srow svg { width:18px; height:18px; fill:var(--muted); }
    .solar.on .srow svg, .solar.ok .srow svg { fill:var(--sun); }
    .solar .srow b { margin-left:auto; color:var(--text); font-weight:600; font-size:1rem; }
    .solar .sbar { height:6px; border-radius:3px; background:var(--line); margin:8px 0 4px; overflow:hidden; }
    .solar .sbar i { display:block; height:100%; background:var(--sun); border-radius:3px; }
    .solar .sfoot { font-size:.72rem; color:var(--muted); }
    .pill.ptop.sun { background:var(--sun); color:#2A2000; }
    .bar.plan.pv { fill:var(--accent); opacity:.45; }
    .note.preview { color:var(--accent); }
    .note.warn { color:#F5A142; border-left:3px solid #F5A142; padding-left:9px; }
    .plansum.preview b { opacity:.75; }

    /* cars view */
    .cars { display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:10px; }
    .cartile { background:var(--panel); border:1px solid transparent; border-radius:16px; padding:12px; text-align:left; color:var(--text); font:inherit; cursor:pointer; display:flex; flex-direction:column; gap:8px; }
    .cartile.active { border-color:var(--accent); }
    .cimg { position:relative; height:110px; display:flex; align-items:center; justify-content:center; color:var(--muted); }
    .cimg img { max-width:100%; max-height:110px; object-fit:contain; }
    .cimg svg { width:56px; height:56px; }
    .chip { position:absolute; top:0; right:0; background:#1C2129; color:#EDF0F4; border-radius:999px; padding:3px 9px; font-size:.75rem; font-weight:600; display:flex; align-items:center; gap:5px; }
    .chip .dot { background:#E5484D; }
    .chip.on .dot { background:#45D69A; }
    .chead { display:flex; justify-content:space-between; align-items:baseline; gap:8px; }
    .chead b { font-weight:600; }
    .chead span, .cfoot { font-size:.76rem; color:var(--muted); }
    header { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
    .title { display:flex; flex-direction:column; gap:2px; }
    .name { font-size:1.05rem; font-weight:600; letter-spacing:.01em; }
    .model { font-size:.8rem; color:var(--muted); }
    .online { width:9px; height:9px; border-radius:50%; background:#59616D; }
    .online.on { background:#45D69A; box-shadow:0 0 0 3px rgba(69,214,154,.15); }

    .hero { display:grid; grid-template-columns:118px 1fr; gap:20px; align-items:center; padding:6px 0 18px; }
    .post {
      position:relative; width:118px; aspect-ratio:301 / 405; justify-self:center;
      background:center / contain no-repeat;
      filter:drop-shadow(0 12px 18px rgba(0,0,0,.45));
    }
    /* sits exactly on the light strip of the photo */
    .strip {
      position:absolute; left:50%; top:28.4%; height:24.2%; width:1.8%; min-width:2px; transform:translateX(-50%);
      border-radius:3px; background:var(--led); box-shadow:0 0 8px var(--led), 0 0 20px color-mix(in srgb, var(--led) 45%, transparent);
      overflow:hidden;
    }
    .strip i { position:absolute; left:0; right:0; height:40%; background:linear-gradient(to top, transparent, rgba(255,255,255,.85), transparent); opacity:0; }
    .strip.flow i { opacity:1; animation:flow 1.8s linear infinite; }
    .strip.breathe { animation:breathe 3.2s ease-in-out infinite; }
    .strip.blink { animation:blink 1s steps(2) infinite; }
    @keyframes flow { from { bottom:-40%; } to { bottom:100%; } }
    @keyframes breathe { 0%,100% { opacity:.45; } 50% { opacity:1; } }
    @keyframes blink { 50% { opacity:.25; } }
    @media (prefers-reduced-motion: reduce) { .strip, .strip i { animation:none !important; } }

    .status { font-size:.95rem; color:var(--led); font-weight:600; }
    .power { display:flex; align-items:baseline; gap:6px; margin:2px 0 4px; }
    .big { font-size:3rem; font-weight:300; line-height:1; letter-spacing:-.02em; font-variant-numeric:tabular-nums; }
    .unit { font-size:1rem; color:var(--muted); }
    .smartline { font-size:.82rem; color:var(--muted); min-height:1.1em; }
    .facts { display:flex; gap:18px; margin:12px 0 0; }
    .facts div { display:flex; flex-direction:column-reverse; }
    .facts dt { font-size:.72rem; color:var(--muted); }
    .facts dd { margin:0; font-size:.98rem; font-variant-numeric:tabular-nums; }

    .eqrow { width:100%; display:flex; align-items:center; gap:12px; background:var(--panel); border:0; border-radius:12px; padding:10px 12px; margin:0 0 12px; color:var(--text); font:inherit; text-align:left; cursor:pointer; }
    .eqimg { width:40px; height:48px; object-fit:contain; flex:none; filter:drop-shadow(0 2px 4px rgba(0,0,0,.35)); }
    .eqinfo { flex:1; min-width:0; display:flex; flex-direction:column; gap:3px; }
    .eqinfo > span { font-size:.8rem; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .eqhead { display:flex; align-items:center; gap:8px; font-size:.86rem; }
    .eqhead b { font-weight:600; }
    .eqhead .online { position:static; }
    .eqbars { display:flex; align-items:flex-end; gap:3px; height:28px; flex:none; }
    .eqbars i { width:6px; border-radius:2px; background:var(--accent); display:block; }
    .eqbars i.warm { background:#F5A623; } .eqbars i.hot { background:#FF5A5F; }
    .eqhero { display:flex; align-items:center; gap:16px; margin-bottom:12px; }
    .eqhero img { width:110px; height:132px; object-fit:contain; flex:none; filter:drop-shadow(0 6px 14px rgba(0,0,0,.45)); }
    .eqmeta { display:flex; flex-direction:column; gap:4px; min-width:0; }
    .eqmeta b { font-size:1.05rem; font-weight:600; }
    .eqmeta > span { font-size:.8rem; color:var(--muted); }
    .eqmeta .state { display:inline-flex; align-items:center; gap:6px; }
    .eqmeta .state .dot { width:8px; height:8px; border-radius:50%; background:var(--muted); display:inline-block; }
    .eqmeta .state.ok .dot { background:#3DDC84; } .eqmeta .state.bad .dot { background:#FF5A5F; }
    .eqkw { font-size:2.4rem; font-weight:300; line-height:1; margin-top:6px; }
    .eqkw small { font-size:1rem; color:var(--muted); }
    .eqkw.out { color:#3DDC84; }
    .eqdir { font-size:.8rem; color:var(--muted); }
    .eqphases { margin:14px 0 6px; }
    .sectitle.eqsub { margin-top:8px; }
    ha-card.light .eqhero img, ha-card.light .eqimg { filter:drop-shadow(0 4px 10px rgba(20,24,30,.25)); }
    .car { display:flex; align-items:center; gap:12px; background:var(--panel); border-radius:12px; padding:10px 12px; margin:0 0 12px; }
    .carimg { width:64px; height:40px; object-fit:contain; flex:none; border-radius:6px; }
    .carimg.placeholder { display:flex; align-items:center; justify-content:center; color:var(--muted); }
    .carimg.placeholder svg { width:30px; height:30px; }
    .carinfo { flex:1; min-width:0; display:flex; flex-direction:column; gap:6px; }
    .carhead { display:flex; justify-content:space-between; align-items:baseline; gap:8px; font-size:.86rem; min-width:0; }
    .carhead b { font-weight:600; flex:none; }
    .carhead span { color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
    .socbar { position:relative; height:6px; border-radius:3px; background:#2A303A; }
    .socbar i { display:block; height:100%; border-radius:3px; background:var(--led); transition:width .6s ease; }
    .socbar em { position:absolute; top:-3px; width:2px; height:12px; background:var(--text); opacity:.7; transform:translateX(-1px); }
    .iconbtn { flex:none; width:34px; height:34px; border-radius:10px; border:1px solid var(--line); background:none; color:var(--text); cursor:pointer; display:flex; align-items:center; justify-content:center; }
    .iconbtn svg { width:18px; height:18px; }
    .grid3.ere { margin-top:8px; }
    .modes { display:grid; grid-auto-flow:column; grid-auto-columns:1fr; background:var(--panel); border-radius:12px; padding:3px; gap:3px; }
    .mode { background:none; border:0; color:var(--muted); padding:9px 4px; border-radius:9px; font:inherit; font-size:.82rem; cursor:pointer; }
    .mode.sel { background:#2C3440; color:var(--text); }

    .tabs { display:flex; gap:18px; margin:16px 2px 10px; border-bottom:1px solid var(--line); }
    .tab { background:none; border:0; color:var(--muted); font:inherit; font-size:.85rem; padding:6px 0 9px; cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px; }
    .tab.sel { color:var(--text); border-bottom-color:var(--accent); }
    button:focus-visible, input:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }

    .actions { display:flex; gap:8px; margin:4px 0 12px; }
    .act { flex:1; background:var(--panel); color:var(--text); border:1px solid var(--line); border-radius:12px; padding:11px 8px; font:inherit; font-size:.88rem; cursor:pointer; }
    .act.primary { background:var(--accent); border-color:var(--accent); color:#06121F; font-weight:600; }
    .act.on { border-color:var(--led); color:var(--led); }
    .act[disabled] { opacity:.4; cursor:default; }
    .act.wide { width:100%; margin-top:12px; }

    .grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
    .tile { background:var(--panel); border-radius:12px; padding:10px 11px; display:flex; flex-direction:column; gap:2px; min-width:0; }
    .tile span, .tile small { font-size:.72rem; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .tile b { font-weight:500; font-size:1.02rem; font-variant-numeric:tabular-nums; }
    .note { color:var(--muted); font-size:.82rem; margin:10px 2px 0; line-height:1.45; }

    .controls { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:12px; }
    .ctl { background:var(--panel); border-radius:12px; padding:9px 11px; display:flex; flex-direction:column; gap:4px; }
    .ctl > span { font-size:.72rem; color:var(--muted); }
    .ctl input { background:none; border:0; color:var(--text); font:inherit; font-size:1rem; padding:0; color-scheme:dark; }
    .stepper { display:flex; align-items:center; justify-content:space-between; gap:4px; }
    .stepper button { width:26px; height:26px; border-radius:8px; border:1px solid var(--line); background:none; color:var(--text); cursor:pointer; font-size:1rem; line-height:1; }
    .stepper b, b.plain { font-weight:500; font-size:.98rem; white-space:nowrap; }

    .chart { margin:0; }
    .chart svg { width:100%; height:140px; display:block; overflow:visible; }
    .bar { fill:#3A4250; }
    .bar.plan { fill:var(--accent); }
    .zero { stroke:var(--line); stroke-width:1; }
    .nowline { stroke:#fff; stroke-width:1.5; stroke-dasharray:3 3; opacity:.7; }
    .chart .plot { position:relative; }
    .ctlhead { display:flex; align-items:center; justify-content:space-between; gap:4px; white-space:nowrap; }
    .unitsw { display:inline-flex; border:1px solid var(--line, rgba(255,255,255,.14)); border-radius:999px; overflow:hidden; }
    .unitsw button { all:unset; cursor:pointer; font-size:10px; line-height:1; padding:3px 5px; color:var(--muted); }
    .unitsw button.on { background:var(--accent, #3b82f6); color:#fff; }
    .clbl { position:absolute; transform:translateY(-85%); font-size:11px; line-height:1; color:var(--muted); white-space:nowrap; pointer-events:none; font-variant-numeric:tabular-nums; letter-spacing:.01em; }
    figcaption { font-size:.74rem; color:var(--muted); display:flex; align-items:center; gap:6px; margin-top:2px; }
    .bar.sun { fill:var(--sun); }
    .sunplan { fill:var(--sun); opacity:.55; }
    .estrip .eg { fill:var(--accent); } .estrip .eu { fill:var(--sun); }
    .estrip.plan .eg, .estrip.plan .eu { opacity:.45; }
    .clbl.smax { font-size:10px; }
    .clbl.tick { transform:translate(-50%,-85%); }
    .key.eg { width:10px; height:10px; border-radius:3px; background:var(--accent); display:inline-block; margin-left:4px; }
    .key.eu { width:10px; height:10px; border-radius:3px; background:var(--sun); display:inline-block; margin-left:6px; }
    .daynav { display:flex; align-items:center; justify-content:center; gap:10px; margin:6px 0 2px; font-size:.82rem; font-weight:600; }
    .daynav span { min-width:70px; text-align:center; }
    .navbtn { width:26px; height:26px; border-radius:8px; border:1px solid var(--line); background:var(--panel); color:var(--text); font:inherit; font-size:1rem; line-height:1; cursor:pointer; }
    .navbtn:disabled { opacity:.3; cursor:default; }
    .legend { display:flex; flex-wrap:wrap; align-items:center; gap:4px 12px; font-size:.72rem; color:var(--muted); }
    .legend span { display:inline-flex; align-items:center; gap:5px; white-space:nowrap; }
    .legend .key { margin:0; }
    .sunreal { fill:none; stroke:var(--sun); stroke-width:2; vector-effect:non-scaling-stroke; opacity:.9; }
    .key.sunreal { width:14px; height:0; border-top:2px solid var(--sun); display:inline-block; }
    .stripkey { font-size:.72rem; color:var(--muted); margin:3px 0 0; display:flex; flex-wrap:wrap; align-items:center; gap:4px 12px; }
    .stripkey span { display:inline-flex; align-items:center; gap:5px; white-space:nowrap; }
    .stripkey .key { margin:0; }
    .bar.past { opacity:.45; }
    .chart.withstrip svg { height:180px; }
    .sunline { fill:none; stroke:var(--sun); stroke-width:2; stroke-dasharray:4 4; vector-effect:non-scaling-stroke; }
    .clbl.sunmax { color:var(--sun); font-size:11px; }
    .key.dots { width:14px; height:0; border-top:2px dashed var(--sun); display:inline-block; vertical-align:middle; margin-left:6px; }
    .key.sunblk { width:10px; height:10px; border-radius:3px; background:var(--sun); opacity:.55; display:inline-block; margin-left:6px; }
    .sunsum { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:10px; }
    .sunline-note { margin:8px 0 0; }
    .key.sun { width:10px; height:10px; border-radius:3px; background:var(--sun); display:inline-block; }
    .chartnote { margin:6px 0 0; }
    .key.plan { width:10px; height:10px; border-radius:3px; background:var(--accent); display:inline-block; }
    .plansum { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }
    .plansum div { display:flex; flex-direction:column; gap:2px; }
    .plansum span { font-size:.72rem; color:var(--muted); }
    .plansum b { font-weight:500; font-size:1.05rem; }

    .flow { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:14px; }
    .flow div { display:flex; flex-direction:column; gap:2px; }
    .flow span, .flow small { font-size:.72rem; color:var(--muted); }
    .flow b { font-size:1.35rem; font-weight:400; font-variant-numeric:tabular-nums; }
    .flow.out div:first-child b { color:#FFD54F; }
    .phases { display:flex; flex-direction:column; gap:10px; margin-bottom:14px; }
    .phase { display:grid; grid-template-columns:22px 1fr 58px 42px; align-items:center; gap:10px; font-size:.85rem; }
    .phase span, .phase small { color:var(--muted); }
    .phase b { font-weight:500; text-align:right; font-variant-numeric:tabular-nums; }
    .track { height:8px; border-radius:4px; background:var(--panel); overflow:hidden; }
    .track i { display:block; height:100%; background:#45D69A; border-radius:4px; transition:width .6s ease; }
    .track i.warm { background:#F4B740; } .track i.hot { background:#FF5C61; }

    .months { display:flex; gap:10px; align-items:flex-end; height:92px; margin:14px 2px 4px; }
    .mcol { flex:1; height:100%; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; gap:4px; }
    .mcol i { width:100%; max-width:30px; background:#3A4250; border-radius:5px 5px 2px 2px; }
    .mcol:last-child i { background:var(--accent); }
    .mcol span { font-size:.7rem; color:var(--muted); }
    h4 { font-size:.8rem; font-weight:500; color:var(--muted); margin:14px 2px 6px; }
    .sessions { list-style:none; margin:0; padding:0; }
    .sessions li { display:grid; grid-template-columns:1fr auto auto; gap:12px; padding:8px 2px; border-bottom:1px solid var(--line); font-size:.84rem; }
    .sessions li span { color:var(--muted); }
    .sessions em { font-style:normal; min-width:62px; text-align:right; }
    .sessions b { font-weight:500; }

    @container (max-width: 420px) {
      .hero { grid-template-columns:88px 1fr; gap:14px; }
      .post { width:88px; }
      .big { font-size:2.5rem; }
      .controls { grid-template-columns:1fr 1fr; }
      .controls .ctl:last-child { grid-column:1 / -1; }
      .facts { gap:12px; }
    }
  `;

  // ------------------------------------------------------------------- editor
  class EaseeSmartCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = config;
      this._render();
    }
    set hass(hass) {
      this._hass = hass;
      this._render();
    }
    _render() {
      if (!this._hass || !this._config) return;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = (s) => ({ entity: "Easee Smart Charging status", name: "Name", title: "Title / Titel", theme: "Theme / Thema", tab: "Start tab", mode_banner: "Mode bar in the charge-mode card / Modusbalk in de laadmodus-kaart", language: "Language / Taal / Sprache" }[s.name] || s.name);
        this._form.addEventListener("value-changed", (ev) => {
          this._config = ev.detail.value;
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      this._form.hass = this._hass;
      this._form.data = this._config;
      this._form.schema = [
        { name: "entity", selector: { entity: { integration: "easee_smart", domain: "sensor" } } },
        { name: "name", selector: { text: {} } },
        { name: "title", selector: { text: {} } },
        { name: "theme", selector: { select: { mode: "dropdown", options: [
          { value: "auto", label: "Auto" }, { value: "dark", label: "Dark / Donker" }, { value: "light", label: "Light / Licht" } ] } } },
        { name: "tab", selector: { select: { mode: "dropdown", options: ["charge", "plan", "grid", "history"] } } },
        { name: "mode_banner", selector: { boolean: {} } },
        {
          name: "language",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "auto", label: "Automatic (Home Assistant)" },
                { value: "nl", label: "Nederlands" },
                { value: "en", label: "English" },
                { value: "de", label: "Deutsch" },
              ],
            },
          },
        },
      ];
    }
  }

  const EXTRA = [
    ["charger", "Laadpaal / Charger", "Big charger with power, status and price."],
    ["modes", "Laadmodus / Charge mode", "Charge mode buttons, boost and pause."],
    ["cars", "Auto's / Cars", "All linked cars with battery level; tap to choose."],
    ["plan", "Planning", "Departure time, target and price chart."],
    ["grid", "Aansluiting / Grid", "Grid power, phases and main fuse."],
    ["costs", "Kosten / Costs", "Costs, ERE, sessions and report."],
    ["equalizer", "Equalizer", "Easee Equalizer: grid power, phases, fuse and meter readings."],
  ];
  // Some setups load a scoped custom-element registry polyfill *after* this script.
  // That polyfill forgets earlier definitions, so Lovelace reports "Custom element doesn't exist".
  // Register (again) until the active registry knows every card.
  const DEFS = [["easee-smart-card", EaseeSmartCard], ["easee-smart-card-editor", EaseeSmartCardEditor]];
  for (const [view] of EXTRA) {
    DEFS.push([`easee-smart-${view}-card`, class extends EaseeSmartCard { static get VIEW() { return view; } }]);
  }
  const register = () => {
    for (const [tag, cls] of DEFS) {
      if (customElements.get(tag)) continue;
      try {
        customElements.define(tag, cls);
      } catch (_e) {
        try { customElements.define(tag, class extends cls {}); } catch (_e2) { /* already known */ }
      }
    }
  };
  register();
  for (const ms of [0, 300, 1000, 2500, 5000, 10000, 20000]) setTimeout(register, ms);
  window.addEventListener("load", register);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === "easee-smart-card")) {
    window.customCards.push({
      type: "easee-smart-card",
      name: "Easee Smart Charging",
      description: "Charger, smart charging, Equalizer and costs in one card.",
      preview: true,
      documentationURL: "https://github.com/George-120/ha-easee-smart",
    });
  }
  for (const [view, label, description] of EXTRA) {
    const type = `easee-smart-${view}-card`;
    if (!window.customCards.some((c) => c.type === type)) {
      window.customCards.push({ type, name: `Easee Smart Charging – ${label}`, description, preview: true, documentationURL: "https://github.com/George-120/ha-easee-smart" });
    }
  }
  console.info(`%c EASEE-SMART-CARD %c ${VERSION} `, "background:#5AA9FF;color:#06121F;font-weight:600", "background:#14181E;color:#EDF0F4");
})();
