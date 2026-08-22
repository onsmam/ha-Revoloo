# Revoloo for Home Assistant

A HACS custom integration for Revoloo (Notty Cat branded) smart pet devices:
the automatic litter box, the water fountain and the automatic feeder — plus
per-cat activity stats.

This was built by reverse-engineering a mitmproxy capture of the official
app's traffic against `api.nottycat.com`. There is no known public API
documentation and no OAuth/login flow was ever observed in the capture, so
this integration authenticates with a static bearer token and `hzuid` header
value copied out of the app.

## Getting your token

1. Set up [mitmproxy](https://mitmproxy.org/) (or any TLS-intercepting proxy)
   between your phone and the internet, with the app's cert pinning disabled
   or the proxy's CA trusted on the device.
2. Open the Notty Cat / Revoloo app and let it load your devices.
3. Find any request to `api.nottycat.com` and copy two request header values:
   - `authorization` — a long opaque string. **Do not** prefix it with
     `Bearer `, the app itself sends the raw value.
   - `hzuid` — a short numeric string.
4. In Home Assistant, add the integration (`Settings → Devices & services →
   Add integration → Revoloo`) and paste both values in.

The token appears to be long-lived (no refresh flow was seen), but if it
ever stops working the integration will prompt you to re-authenticate with a
freshly captured pair.

## What you get

For every litter box, water fountain and feeder on the account:

- **Sensors**: last event log line, remaining consumable days (litter,
  garbage bags, filter, desiccant), planned portion size, meals fed today
  (total/auto/manual), water fountain status, and more.
- **Binary sensors**: read-only state for toggles observed in the app but for
  which no "set" API call was ever captured (litter/garbage-bag/filter
  reminder switches, pet-present, water flowing, UVC lamp active, food
  available — see [Known limitations](#known-limitations)).
- **Controls**:
  - Litter box: mode select (Auto / Schedule / Smart), button-lock switch,
    litter-reminder and garbage-bag-reminder cycle (days, resets the
    countdown when changed), auto-clean delay (1-15 min), "Clean now" and
    "Smooth litter" buttons.
  - Water fountain: mode select (Off / Continuous / Interval), UVC
    sterilization switch, LED switch, "Reset filter" button, "Sterilize"
    button.
  - Feeder: LED switch, function-button-lock switch, desiccant-reminder
    switch, manual feed portion size, "Dispense food" and "Reset desiccant"
    buttons.

For every cat on the account: today's weight (kg), litter box / eating /
drinking visit counts, their durations (seconds, with yesterday's value and
the app's own "+N"/"-N" difference as attributes), and the app's own
"Normal"/"Attention" status for each of those plus overall weight status.

## Known limitations

The captured traffic never included a request that changes the following
settings, even though their current value is visible via the sensors above.
They are exposed read-only for now:

- Litter box: ozone deodorization, voice prompts, do-not-disturb schedule.
  Also, the litter box's "Smooth litter" one_key value (3) and the "Empty
  litter" value (guessed as 2) are the device owner's best guess from the
  app's UI rather than captured traffic — "Empty litter" isn't wired up yet
  pending their confirmation.
- Water fountain: do-not-disturb schedule.
- Feeder: automatic/planned portion sizes (still read-only sensors), feeding
  schedule.

If you can capture the corresponding requests (e.g. by toggling these in the
app while running mitmproxy) please open an issue or PR with the
request/response bodies and they can be wired up as proper controls.

## Polling interval

The default poll interval is 10 minutes; it can be changed from the
integration's options (`Configure` on the integration card).
