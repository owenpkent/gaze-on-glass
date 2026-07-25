# Gaze output protocol

How the Gaze on Glass service publishes gaze to other apps on the same phone.

Status: draft v0. Nothing consumes it yet. It is specified now so the app is built against a contract rather than growing one, and so a consumer written today does not have to be rewritten when the app ships.

## Design constraints

- Single device, loopback only. No network exposure, no discovery, no pairing.
- 30Hz per eye. Small messages, no allocation storms, no schema negotiation.
- Consumers are ordinary Android apps that should not need a native library or an AIDL binding to read a coordinate.
- A late consumer must be able to attach mid-session and immediately know the screen geometry and calibration state, without waiting for a special frame.

## Transport

Primary: **line-delimited JSON over a loopback TCP socket**, default port **7371**, bound to `127.0.0.1` only.

Chosen over a Unix domain socket (awkward to reach across Android app sandboxes), a Binder service (forces consumers into an AIDL dependency), and broadcast Intents (per-message system overhead at 30Hz, and the delivery latency is not worth it). A loopback socket is readable from any language and any framework on the device, including a WebView, which keeps the "any local app can consume it" promise honest.

Each message is one UTF-8 JSON object followed by `\n`. No framing beyond the newline, no length prefix. Consumers read lines and parse.

The server accepts multiple concurrent clients and broadcasts to all of them. It never blocks on a slow client: if a client's send buffer is full, its pending gaze frames are dropped, not queued. Gaze is a live signal; a stale coordinate is worse than a missing one.

## Messages

Every message has a `type` and a monotonic `t` in microseconds since an arbitrary epoch (use `SystemClock.elapsedRealtimeNanos() / 1000`). Wall-clock time is not used: it can jump.

### `hello`

Sent once to every client immediately on connect, before any `gaze`. This is what lets a consumer attach mid-session.

```json
{
  "type": "hello",
  "t": 182734981234,
  "protocol": 0,
  "service": "gaze-on-glass/0.1.0",
  "screen": { "width": 1920, "height": 1080 },
  "eyes": ["left", "right"],
  "rate_hz": 30,
  "calibrated": true,
  "profile": { "id": "2026-07-25-rev-a", "mean_error_deg": 0.84 }
}
```

`calibrated` false means `gaze` messages will still flow but `x`/`y` are unmapped and meaningless. `profile` is null when uncalibrated.

### `gaze`

The stream. One per processed frame pair.

```json
{
  "type": "gaze",
  "t": 182734981567,
  "x": 0.4213,
  "y": 0.6688,
  "confidence": 0.93,
  "eyes": {
    "left":  { "x": 0.4190, "y": 0.6702, "confidence": 0.95, "pupil": [0.512, 0.447] },
    "right": { "x": 0.4236, "y": 0.6674, "confidence": 0.91, "pupil": [0.488, 0.451] }
  }
}
```

- `x`, `y`: normalized screen position, origin top-left, matching Android's convention. **Not clamped to 0..1.** A gaze off the edge of the display is a real observation, and clamping it silently turns "looking away" into "staring at the border". Consumers that need a clamped value clamp it themselves.
- `confidence`: 0..1, the confidence-weighted combination across eyes. **0 means the pupil was not detected this frame**, and `x`/`y` must be ignored. The message is still sent, because a consumer needs to distinguish "not looking" from "service died".
- `eyes`: per-eye detail. Optional; a consumer only doing screen pointing can ignore it entirely. `pupil` is the normalized position in the eye image, useful for debugging and for anyone wanting to run their own mapping.

### `status`

Sent on change only, not periodically.

```json
{
  "type": "status",
  "t": 182734990000,
  "state": "tracking",
  "detail": "",
  "calibrated": true
}
```

`state` is one of:

| state | meaning |
| --- | --- |
| `starting` | Service up, cameras not yet streaming. |
| `no_camera` | UVC device absent or lost. Check the hub and Gate 1. |
| `uncalibrated` | Streaming frames, no valid calibration profile loaded. |
| `calibrating` | A calibration session is in progress; `gaze` may pause. |
| `tracking` | Normal operation. |
| `degraded` | Streaming below target rate, or one eye lost. `detail` says which. |
| `stopping` | Shutting down; the socket closes after this. |

A consumer that only handles `gaze` and ignores `status` still works. That is deliberate.

## Consumer sketch

```kotlin
Socket("127.0.0.1", 7371).use { sock ->
    val reader = sock.getInputStream().bufferedReader()
    for (line in reader.lineSequence()) {
        val msg = JSONObject(line)
        if (msg.getString("type") != "gaze") continue
        if (msg.getDouble("confidence") <= 0.0) continue   // pupil lost
        onGaze(msg.getDouble("x"), msg.getDouble("y"))
    }
}
```

## Open questions

- Whether to offer a second, lower-overhead binary framing for consumers that care (fixed 32-byte packed struct on a second port). Deferred until something actually feels the JSON cost at 30Hz, which it may well not.
- Whether the app should also expose a ContentProvider for one-shot "where is the user looking right now" queries, for consumers that do not want a persistent socket.
- Authentication. Currently none: any app on the device can read the stream. On a personal single-user device that is arguably correct, but it is a decision, not an oversight, and it should be revisited before any wider release.

## Versioning

`protocol` in `hello` is an integer, bumped on any breaking change. Additive fields do not bump it, so consumers must ignore unknown fields rather than reject them. Protocol 0 is unstable by definition: it will change without ceremony until the gates in the root README pass and the app exists.
