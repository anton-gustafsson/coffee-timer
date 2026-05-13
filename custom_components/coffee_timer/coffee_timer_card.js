// ─── Card Editor ────────────────────────────────────────────────────────────

class CoffeeTimerCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._schema = [
      { name: "name", selector: { text: {} } },
      {
        name: "switch_entity",
        selector: { entity: { domain: "switch" } },
      },
      {
        name: "time_entity",
        selector: { entity: { domain: "time" } },
      },
    ];
    this._labels = {
      name: "Card Title",
      switch_entity: "Switch Entity (coffee_timer Enabled)",
      time_entity: "Time Entity (coffee_timer Brew Time)",
    };
  }

  setConfig(config) {
    this._config = config;
    if (this._form) this._form.data = this._config;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._form) this._buildForm();
    this._form.hass = hass;
  }

  _buildForm() {
    const form = document.createElement("ha-form");
    form.schema = this._schema;
    form.data = this._config;
    form.hass = this._hass;
    form.computeLabel = (s) => this._labels[s.name] ?? s.name;
    form.addEventListener("value-changed", (ev) => {
      this._config = ev.detail.value;
      this.dispatchEvent(
        new CustomEvent("config-changed", { detail: { config: this._config } })
      );
    });
    this.appendChild(form);
    this._form = form;
  }
}

customElements.define("coffee-timer-card-editor", CoffeeTimerCardEditor);

// ─── Card ────────────────────────────────────────────────────────────────────

class CoffeeTimerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
  }

  static getConfigElement() {
    return document.createElement("coffee-timer-card-editor");
  }

  static getStubConfig() {
    return {
      name: "Coffee Timer",
      switch_entity: "",
      time_entity: "",
    };
  }

  setConfig(config) {
    if (!config.switch_entity || !config.time_entity) {
      throw new Error("coffee-timer-card requires switch_entity and time_entity");
    }
    this._config = config;
    this._buildDom();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _buildDom() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 20px 16px 16px; }

        .header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 18px;
        }
        .header-icon { font-size: 2em; line-height: 1; }
        .header-text { flex: 1; }
        .header-title {
          font-size: 1.1em;
          font-weight: 600;
          color: var(--primary-text-color);
        }
        .header-status {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }

        .time-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 16px;
          padding: 10px 12px;
          border-radius: 8px;
          background: var(--secondary-background-color);
        }
        .time-label {
          font-size: 0.9em;
          color: var(--secondary-text-color);
        }
        input[type="time"] {
          background: transparent;
          border: none;
          color: var(--primary-text-color);
          font-size: 1.3em;
          font-weight: 500;
          font-family: inherit;
          cursor: pointer;
          outline: none;
          padding: 0;
        }
        input[type="time"]::-webkit-calendar-picker-indicator {
          filter: invert(var(--is-dark-mode, 0));
          cursor: pointer;
        }

        .toggle-btn {
          width: 100%;
          padding: 12px;
          border: none;
          border-radius: 8px;
          font-size: 0.95em;
          font-weight: 600;
          letter-spacing: 0.05em;
          cursor: pointer;
          transition: background 0.2s, opacity 0.2s;
        }
        .toggle-btn.enabled {
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
        }
        .toggle-btn.disabled {
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color);
        }
        .toggle-btn:active { opacity: 0.8; }

        .error-banner {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          border-radius: 8px;
          background: var(--error-color, #db4437);
          color: #fff;
        }
        .error-icon { font-size: 1.5em; flex-shrink: 0; }
        .error-title { font-weight: 600; margin-bottom: 2px; }
        .error-message { font-size: 0.85em; opacity: 0.9; }
      </style>

      <ha-card>
        <div id="content">
          <div class="header">
            <div class="header-icon">☕</div>
            <div class="header-text">
              <div class="header-title" id="title">Coffee Timer</div>
              <div class="header-status" id="status">Not scheduled</div>
            </div>
          </div>

          <div class="time-row">
            <span class="time-label">Brew time</span>
            <input type="time" id="time-input" />
          </div>

          <button class="toggle-btn disabled" id="toggle-btn">Enable</button>
        </div>

        <div id="error" style="display:none">
          <div class="error-banner">
            <span class="error-icon">⚠️</span>
            <div>
              <div class="error-title">Integration unavailable</div>
              <div class="error-message" id="error-message">Coffee Timer integration is not loaded.</div>
            </div>
          </div>
        </div>
      </ha-card>
    `;

    this.shadowRoot.getElementById("time-input").addEventListener("change", (e) => {
      if (!this._hass || !this._config) return;
      const [h, m] = e.target.value.split(":");
      this._hass.callService("time", "set_value", {
        entity_id: this._config.time_entity,
        time: `${h}:${m}:00`,
      });
    });

    this.shadowRoot.getElementById("toggle-btn").addEventListener("click", () => {
      if (!this._hass || !this._config) return;
      const sw = this._hass.states[this._config.switch_entity];
      if (!sw) return;
      const svc = sw.state === "on" ? "turn_off" : "turn_on";
      this._hass.callService("switch", svc, { entity_id: this._config.switch_entity });
    });
  }

  _showError(message) {
    const content = this.shadowRoot.getElementById("content");
    const error = this.shadowRoot.getElementById("error");
    const msg = this.shadowRoot.getElementById("error-message");
    if (content) content.style.display = "none";
    if (error) error.style.display = "block";
    if (msg) msg.textContent = message;
  }

  _showContent() {
    const content = this.shadowRoot.getElementById("content");
    const error = this.shadowRoot.getElementById("error");
    if (content) content.style.display = "block";
    if (error) error.style.display = "none";
  }

  _render() {
    if (!this._hass || !this._config || !this.shadowRoot.getElementById("title")) return;

    const sw = this._hass.states[this._config.switch_entity];
    const timeEnt = this._hass.states[this._config.time_entity];

    if (!sw || !timeEnt) {
      this._showError("Coffee Timer integration is not installed or has been removed.");
      return;
    }

    if (sw.state === "unavailable" || timeEnt.state === "unavailable") {
      this._showError("Coffee Timer integration is unavailable. Check HA logs for details.");
      return;
    }

    this._showContent();

    const isOn = sw.state === "on";
    const hhmm = (timeEnt.state || "07:00:00").slice(0, 5);

    this.shadowRoot.getElementById("title").textContent =
      this._config.name || "Coffee Timer";

    const statusEl = this.shadowRoot.getElementById("status");
    if (isOn) {
      const nextBrewIso = sw.attributes?.next_brew_time;
      if (nextBrewIso) {
        const next = new Date(nextBrewIso);
        const dateStr = next.toLocaleDateString(undefined, {
          weekday: "short",
          month: "short",
          day: "numeric",
        });
        statusEl.textContent = `Scheduled ${dateStr} at ${hhmm}`;
      } else {
        statusEl.textContent = `Scheduled at ${hhmm}`;
      }
    } else {
      statusEl.textContent = "Not scheduled";
    }

    const timeInput = this.shadowRoot.getElementById("time-input");
    if (timeInput && this.shadowRoot.activeElement !== timeInput) {
      timeInput.value = hhmm;
    }

    const btn = this.shadowRoot.getElementById("toggle-btn");
    btn.textContent = isOn ? "Disable" : "Enable";
    btn.className = `toggle-btn ${isOn ? "enabled" : "disabled"}`;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("coffee-timer-card", CoffeeTimerCard);
