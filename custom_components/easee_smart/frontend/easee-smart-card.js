/* Easee Smart Charging card — app-style view of an Easee charger, served by the easee_smart integration. */
(() => {
  const VERSION = "1.4.1";
  // Photo of the charger, served next to this script by the integration.
  const CHARGER_IMG = document.currentScript && document.currentScript.src
    ? new URL("charger.webp", document.currentScript.src).href
    : "/easee_smart/charger.webp";

  const I18N = {
    en: {
      tabs: { charge: "Charging", plan: "Planning", grid: "Equalizer", meter: "Grid", history: "History" },
      modes: { normal: "Normal", smart: "Smart", solar: "Solar", solar_smart: "Solar + smart" },
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
      departure: "Ready at", target: "Add", targetSoc: "Charge to", needed: "still needed",
      planStart: "Starts", planEnd: "Ready", planCost: "Estimated", noPlan: "No plan needed right now.",
      noPrices: "Prices could not be fetched yet. They update automatically.",
      now: "now", grid: "Grid", importing: "Importing", exporting: "Exporting", fuse: "Main fuse",
      headroom: "headroom", surplus: "Solar surplus", phase: "Phase", noGrid: "No Equalizer or main connection set. Add your meter under Configure → Main connection.",
      month: "This month", prev: "Previous months", reimb: "Reimbursement", sessions: "Recent sessions",
      export: "Export last month (CSV)", exported: "Report written", today: "Today", none: "No sessions yet.",
      kwh: "kWh", avg: "avg.", amps: "Charge current", planned: "Planned charging", refresh: "Refresh car data", priceNow: "Power now", carsTitle: "Cars", noCars: "No cars linked yet. Add them under Configure → Cars.", pluggedIn: "Plugged in", notPlugged: "Not plugged in", ere: "ERE", year: "This year", total: "Total", range: "range",
    },
    nl: {
      tabs: { charge: "Laden", plan: "Planning", grid: "Equalizer", meter: "Aansluiting", history: "Historie" },
      modes: { normal: "Normaal", smart: "Slim", solar: "Zon", solar_smart: "Zon + slim" },
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
      departure: "Klaar om", target: "Laden", targetSoc: "Laden tot", needed: "nog nodig",
      planStart: "Start", planEnd: "Klaar", planCost: "Verwacht", noPlan: "Er is nu geen planning nodig.",
      noPrices: "De prijzen konden nog niet worden opgehaald. Ze worden vanzelf bijgewerkt.",
      now: "nu", grid: "Net", importing: "Afname", exporting: "Teruglevering", fuse: "Hoofdzekering",
      headroom: "ruimte", surplus: "Zonne-overschot", phase: "Fase", noGrid: "Geen Equalizer of hoofdaansluiting ingesteld. Voeg je meter toe via Configureren → Hoofdaansluiting.",
      month: "Deze maand", prev: "Vorige maanden", reimb: "Vergoeding", sessions: "Recente sessies",
      export: "Vorige maand exporteren (CSV)", exported: "Rapport opgeslagen", today: "Vandaag", none: "Nog geen sessies.",
      kwh: "kWh", avg: "gem.", amps: "Laadstroom", planned: "Gepland laden", refresh: "Gegevens auto verversen", priceNow: "Stroom nu", carsTitle: "Auto's", noCars: "Nog geen auto's gekoppeld. Voeg ze toe via Configureren → Auto's.", pluggedIn: "Aangesloten", notPlugged: "Niet aangesloten", ere: "ERE", year: "Dit jaar", total: "Totaal", range: "actieradius",
    },
    de: {
      tabs: { charge: "Laden", plan: "Planung", grid: "Equalizer", meter: "Anschluss", history: "Verlauf" },
      modes: { normal: "Normal", smart: "Smart", solar: "Solar", solar_smart: "Solar + Smart" },
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
      departure: "Fertig um", target: "Laden", targetSoc: "Laden bis", needed: "noch nötig",
      planStart: "Start", planEnd: "Fertig", planCost: "Erwartet", noPlan: "Derzeit ist keine Planung nötig.",
      noPrices: "Preise konnten noch nicht abgerufen werden. Sie werden automatisch aktualisiert.",
      now: "jetzt", grid: "Netz", importing: "Bezug", exporting: "Einspeisung", fuse: "Hauptsicherung",
      headroom: "Reserve", surplus: "Solarüberschuss", phase: "Phase", noGrid: "Kein Equalizer oder Hausanschluss eingerichtet. Zähler unter Konfigurieren → Hausanschluss hinzufügen.",
      month: "Dieser Monat", prev: "Vormonate", reimb: "Erstattung", sessions: "Letzte Ladevorgänge",
      export: "Letzten Monat exportieren (CSV)", exported: "Bericht gespeichert", today: "Heute", none: "Noch keine Ladevorgänge.",
      kwh: "kWh", avg: "Ø", amps: "Ladestrom", planned: "Geplantes Laden", refresh: "Autodaten aktualisieren", priceNow: "Strom jetzt", carsTitle: "Autos", noCars: "Noch keine Autos verbunden. Unter Konfigurieren → Autos hinzufügen.", pluggedIn: "Angeschlossen", notPlugged: "Nicht angeschlossen", ere: "ERE", year: "Dieses Jahr", total: "Gesamt", range: "Reichweite",
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
      this._render();
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
            ${this._renderView(view, { a, t, status, smart, led, power, name, isOnline, duration })}
          </ha-card>`;
        return;
      }

      this.shadowRoot.innerHTML = `
        <style>${CSS}</style>
        <ha-card class="${this._themeClass()}" style="--led:${led.color}">
          <header>
            <div class="title">
              <span class="name">${esc(name)}</span>
              <span class="model">${esc(a.model || "")}</span>
            </div>
            <span class="online ${isOnline ? "on" : "off"}" title="${isOnline ? "online" : "offline"}"></span>
          </header>

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

          <div class="modes" role="radiogroup">
            ${["normal", "smart", "solar", "solar_smart"]
              .filter((m) => a.has_surplus_source || !m.startsWith("solar"))
              .map((m) => `<button class="mode ${a.mode === m ? "sel" : ""}" data-act="mode" data-mode="${m}" role="radio" aria-checked="${a.mode === m}">${t.modes[m]}</button>`)
              .join("")}
          </div>

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
        default: return "";
      }
    }

    _viewCharger({ a, t, status, smart, led, power, name }) {
      const kw = power !== null && status === "charging" ? this._num(power, 1) : this._num(0, 1);
      const top = a.ere ? `${t.ere} ${t.month.toLowerCase()}: ${this._money(a.ere.month, a.currency)}` : `${t.today}: ${this._money(a.today && a.today.cost, a.currency)}`;
      const car = a.car;
      const statusText = CONNECTED.has(status) ? (car ? `${car.name}${car.soc !== null && car.soc !== undefined ? " · " + this._num(car.soc, 0) + "%" : ""}` : t.status[status] || status) : t.status[status] || status;
      return `
        <div class="bighead"><b>${esc(name)}</b><span>${esc(a.model || "")} · ${esc(t.smart[smart] || "")}</span></div>
        <div class="bigpost" style="background-image:url('${CHARGER_IMG}')">
          <span class="pill ptop">${top}</span>
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
        <div class="bigmodes">
          ${modes.map((m) => `<button class="bigmode ${a.mode === m ? "sel" : ""}" data-act="mode" data-mode="${m}"><svg viewBox="0 0 24 24">${icons[m]}</svg><span>${t.modes[m]}</span></button>`).join("")}
        </div>
        <div class="actions">
          <button class="act primary" data-act="${charging ? "pause" : "resume"}" ${charging || canStart ? "" : "disabled"}>${charging ? t.pause : t.resume}</button>
          <button class="act ${a.boost ? "on" : ""}" data-act="boost" ${CONNECTED.has(status) ? "" : "disabled"}>${t.boost}</button>
        </div>
        <p class="note">${esc(t.smart[a.smart_state] || "")}</p>`;
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
      const useSoc = a.has_soc && ent.target_soc;
      const targetVal = useSoc ? a.target_soc : a.target_energy;
      const step = useSoc ? 5 : 1;
      const unit = useSoc ? "%" : t.kwh;
      const chart = this._priceChart(a, t);
      const summary = a.plan && a.plan.length
        ? `<div class="plansum">
             <div><span>${t.planStart}</span><b>${this._time(a.next_start)}</b></div>
             <div><span>${t.planEnd}</span><b>${this._time(a.complete_by)}</b></div>
             <div><span>${t.planCost}</span><b>${this._money(a.plan_cost, a.currency)}</b></div>
           </div>`
        : `<p class="note">${a.prices && a.prices.length ? t.noPlan : t.noPrices}</p>`;
      return `
        <div class="controls">
          <label class="ctl"><span>${t.departure}</span>
            <input type="time" value="${esc(a.departure || "07:00")}" data-ctl="departure">
          </label>
          <div class="ctl"><span>${useSoc ? t.targetSoc : t.target}</span>
            <div class="stepper">
              <button data-act="step" data-dir="-1" data-step="${step}" aria-label="−">−</button>
              <b>${this._num(targetVal, 0)} ${unit}</b>
              <button data-act="step" data-dir="1" data-step="${step}" aria-label="+">+</button>
            </div>
          </div>
          <div class="ctl"><span>${t.needed}</span><b class="plain">${this._num(a.energy_needed, 1)} ${t.kwh}</b></div>
        </div>
        ${chart}
        ${summary}`;
    }

    _priceChart(a, t) {
      const prices = (a.prices || []).filter((p) => new Date(p.end) > new Date(Date.now() - 3600e3)).slice(0, 96);
      if (!prices.length) return "";
      const planned = new Set((a.plan || []).map((p) => new Date(p.start).getTime()));
      const inPlan = (p) => (a.plan || []).some((s) => new Date(s.start) < new Date(p.end) && new Date(s.end) > new Date(p.start));
      const vals = prices.map((p) => p.price);
      const max = Math.max(...vals, 0.01);
      const lo = Math.min(...vals);
      // all-positive prices: start the axis a bit below the cheapest slot so differences stay visible
      const min = lo < 0 ? lo : Math.max(0, lo - (max - lo) * 0.35);
      const W = 600, H = 120, pad = 2;
      const bw = W / prices.length;
      const y = (v) => H - ((v - min) / (max - min || 1)) * (H - 14) - 2;
      const zero = y(0);
      const now = Date.now();
      let nowX = null;
      const bars = prices.map((p, i) => {
        const s = new Date(p.start).getTime(), e = new Date(p.end).getTime();
        if (now >= s && now < e) nowX = i * bw + ((now - s) / (e - s)) * bw;
        const top = Math.min(y(p.price), zero), h = Math.max(1.5, Math.abs(zero - y(p.price)));
        const cls = inPlan(p) || planned.has(s) ? "bar plan" : "bar";
        return `<rect class="${cls}" x="${(i * bw + pad / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${Math.max(1, bw - pad).toFixed(1)}" height="${h.toFixed(1)}" rx="1.5"><title>${this._time(p.start)} · ${this._num(p.price, 3)}</title></rect>`;
      }).join("");
      const ticks = prices.map((p, i) => {
        const d = new Date(p.start);
        return d.getMinutes() === 0 && d.getHours() % 6 === 0 ? `<text x="${(i * bw).toFixed(1)}" y="${H + 14}">${String(d.getHours()).padStart(2, "0")}:00</text>` : "";
      }).join("");
      return `
        <figure class="chart">
          <svg viewBox="0 -4 ${W} ${H + 20}" preserveAspectRatio="none" role="img">
            <line class="zero" x1="0" x2="${W}" y1="${zero.toFixed(1)}" y2="${zero.toFixed(1)}"></line>
            ${bars}
            ${nowX !== null ? `<line class="nowline" x1="${nowX.toFixed(1)}" x2="${nowX.toFixed(1)}" y1="0" y2="${H}"></line>` : ""}
            ${ticks}
          </svg>
          <figcaption><span class="key plan"></span>${t.planned} · ${this._num(lo, 3)} – ${this._num(max, 3)} ${a.currency || "€"}/kWh</figcaption>
        </figure>`;
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
        case "boost":
          if (ent.boost) await call("switch", a.boost ? "turn_off" : "turn_on", { entity_id: ent.boost });
          return;
        case "lock": {
          const sw = this._hass.states[src.cable_locked_permanently];
          if (sw) await call("switch", sw.state === "on" ? "turn_off" : "turn_on", { entity_id: src.cable_locked_permanently });
          return;
        }
        case "step": {
          const useSoc = a.has_soc && ent.target_soc;
          const id = useSoc ? ent.target_soc : ent.target_energy;
          const cur = useSoc ? a.target_soc : a.target_energy;
          const next = Math.min(useSoc ? 100 : 120, Math.max(useSoc ? 10 : 1, Number(cur) + Number(btn.dataset.dir) * Number(btn.dataset.step)));
          if (id) await call("number", "set_value", { entity_id: id, value: next });
          return;
        }
        case "car":
          if (ent.active_car) await call("select", "select_option", { entity_id: ent.active_car, option: btn.dataset.name });
          return;
        case "refresh":
          if (ent.refresh_car) await call("button", "press", { entity_id: ent.refresh_car });
          return;
        case "export":
          if (ent.export_report) {
            await call("button", "press", { entity_id: ent.export_report });
            this._exported = true;
            this._sig = null;
            this._render();
          }
          return;
        default:
      }
    }

    async _onChange(e) {
      const el = e.target;
      if (el.dataset.ctl === "departure") {
        const ent = this._attrs().entities || {};
        if (ent.departure_time && el.value) {
          await this._hass.callService("time", "set_value", { entity_id: ent.departure_time, time: `${el.value}:00` });
        }
      }
    }
  }

  const CSS = `
    :host { display:block; container-type:inline-size; }
    ha-card {
      display:block;
      --bg:#14181E; --panel:#1C2129; --line:#2A303A; --text:#EDF0F4; --muted:#8C95A2; --accent:#5AA9FF;
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
    .chart text { fill:var(--muted); font-size:11px; }
    figcaption { font-size:.74rem; color:var(--muted); display:flex; align-items:center; gap:6px; margin-top:2px; }
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
        this._form.computeLabel = (s) => ({ entity: "Easee Smart Charging status", name: "Name", title: "Title / Titel", theme: "Theme / Thema", tab: "Start tab", language: "Language / Taal / Sprache" }[s.name] || s.name);
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
  ];
  if (!customElements.get("easee-smart-card")) customElements.define("easee-smart-card", EaseeSmartCard);
  for (const [view] of EXTRA) {
    const tag = `easee-smart-${view}-card`;
    if (!customElements.get(tag)) {
      customElements.define(tag, class extends EaseeSmartCard { static get VIEW() { return view; } });
    }
  }
  if (!customElements.get("easee-smart-card-editor")) customElements.define("easee-smart-card-editor", EaseeSmartCardEditor);
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
