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

Entities are placed in HA's Config or Diagnostic sections where that fits
(settings you'd change go in Config, read-only consumable/status info goes
in Diagnostic); anything not called out below sits in the main section.

### Litter box

- **Sensors**: last event log line, status (idle/cleaning), cleanings today,
  total toilet visits, litter remaining (Diagnostic), garbage bag remaining
  (Diagnostic).
- **Binary sensors** (Diagnostic, read-only — no "set" call was ever
  captured for these): litter sensor enabled, garbage bag holder enabled.
- **Controls**: mode select (Auto / Schedule / Smart), button-lock switch
  (Config), litter-reminder and garbage-bag-reminder on/off switches
  (Config), litter-reminder cycle and garbage-bag-reminder cycle in days —
  resets the countdown when changed (Config), auto-clean delay 1-15 minutes
  (Config), "Clean now" button, "Smooth litter" button.

### Water fountain

- **Sensors**: last event log line, status, filter remaining (Diagnostic).
- **Binary sensors**: water flowing, UVC lamp active, pet present.
- **Controls**: mode select (Off / Continuous / Interval), UVC sterilization
  switch (Config), LED switch (Config), filter-reminder on/off switch
  (Config), "Reset filter" button (Config), "Sterilize" button.

### Feeder

- **Sensors**: last event log line, status, meals fed today (total, auto,
  manual), planned portion size (Config), desiccant remaining (Diagnostic),
  and a read-only "Feeding plans" sensor (Diagnostic) listing the feeder's
  current on-device plans — see
  [Feeding schedule sync](#feeding-schedule-sync).
- **Binary sensors**: food available (Diagnostic, read-only), pet present.
- **Controls**: LED switch, function-button-lock switch (Config),
  desiccant-reminder switch (Config), manual feed portion size 1-10
  (Config, HA-local — see below), "Dispense food" button, "Reset desiccant"
  button (Config), and — only once a `schedule` helper is configured for
  that feeder — a "Sync feeding schedule" button (Config); see
  [Feeding schedule sync](#feeding-schedule-sync).

The manual feed portion size has no equivalent setting on the device itself
— the app's "dispense now" call takes a quantity every time rather than
reading a stored preference — so it's kept as Home-Assistant-local state,
restored across restarts, and read by the "Dispense food" button at press
time.

### Per-cat sensors

For every cat on the account: today's weight in kg (feeds Home Assistant's
long-term statistics), litter box / eating / drinking visit counts, their
durations in seconds (with yesterday's value and the app's own "+N"/"-N"
difference as attributes), and the app's own "Normal"/"Attention" status for
each of those plus overall weight status.

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
- Feeder: automatic/planned portion sizes (still read-only sensors). Feeding
  plans can now be *pushed* from a Home Assistant `schedule` helper (see
  "Feeding schedule sync" below); there's no way to add/remove/edit a single
  plan from Home Assistant directly, only via that one-way sync.

If you can capture the corresponding requests (e.g. by toggling these in the
app while running mitmproxy) please open an issue or PR with the
request/response bodies and they can be wired up as proper controls.

## Feeding schedule sync

A feeder's feeding plans (the times and portion sizes it dispenses food at)
can be driven from a Home Assistant `schedule` helper instead of the app:

1. Create a `schedule` helper (Settings → Automations & Scenes → Helpers) and
   add blocks to it. On each block, set a custom `data` field with a
   `porties` key holding the portion count for that time, e.g. a block from
   `04:00` to `04:01` with `data: {porties: 7}`. The block's *end* time
   doesn't matter — only the start time and the `porties` value are used.
2. In the integration's options (`Configure` on the integration card), pick
   that schedule helper for the feeder.
3. Press the feeder's new "Sync feeding schedule" button (or wait for the
   automatic daily sync at 03:00 local time) to push it to the device.

Syncing **deletes every plan currently on the device and re-adds** the ones
from the schedule helper — it's a one-way, full replace, not a merge. The
device's actual plan list (as last read from the API) is shown separately in
a read-only "Feeding plans" sensor, so you can confirm the push worked. Its
state is a readable summary like `08:00 x1, 19:00 x3` (a plan turned off in
the app shows as `08:00 x1 (off)`); the full list with plan IDs is also
available as an attribute for automations.

The device has no concept of different plans on different days of the week —
every plan is just a `{time, portions}` pair that repeats daily. A
`schedule` helper is inherently weekly, so if you put different blocks on
different days, they all get merged into one shared daily set (a warning is
logged when this happens) rather than silently applied to only one day.

The feeder's API has no bulk add/delete for plans (confirmed: the
`delete_plan` endpoint's backend model only deserializes a single plan at a
time, and a JSON array body is rejected outright), so a sync makes one HTTP
call per plan deleted and re-added rather than a single batched request.
This is unlikely to matter for a normal handful of daily feeding times, but
means a sync with many plans takes a little longer than an instant round
trip.

## Polling interval

The default poll interval is 10 minutes; it can be changed from the
integration's options (`Configure` on the integration card).
