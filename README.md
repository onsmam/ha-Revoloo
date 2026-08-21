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
  garbage bags, filter, desiccant), portion sizes, do-not-disturb schedule,
  firmware version (as an `update` entity), and more.
- **Binary sensors**: read-only state for toggles observed in the app but for
  which no "set" API call was ever captured (ozone, key lock, voice prompts,
  LED, pet-present, etc. — see [Known limitations](#known-limitations)).
- **Controls**:
  - Litter box: mode select (Auto / Schedule / Smart), "Clean now" button,
    "Reset weight calibration" button.
  - Water fountain: mode select (Off / Continuous / Interval), UVC
    sterilization switch, "Reset filter" button, "Sterilize" button.
  - Feeder: "Dispense food" button (dispenses one portion).

For every cat on the account: today's weight (kg), litter box / eating /
drinking visit counts, their durations (seconds, with yesterday's value and
the app's own "+N"/"-N" difference as attributes), and the app's own
"Normal"/"Attention" status for each of those plus overall weight status.

## Known limitations

The captured traffic never included a request that changes the following
settings, even though their current value is visible via the sensors above.
They are exposed read-only for now:

- Litter box: ozone deodorization, button lock, voice prompts, LED,
  do-not-disturb schedule, cleaning delay.
- Water fountain: LED, do-not-disturb schedule.
- Feeder: portion sizes, child lock, desiccant reminder reset, feeding
  schedule.

If you can capture the corresponding requests (e.g. by toggling these in the
app while running mitmproxy) please open an issue or PR with the
request/response bodies and they can be wired up as proper controls.

## Polling interval

The default poll interval is 60 seconds; it can be changed from the
integration's options (`Configure` on the integration card).
