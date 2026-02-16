# Mapping the Zepp/Huami API - A Reverse Engineering Playbook

> How we mapped an undocumented cloud API using traffic interception,
> and what we found. This methodology applies to any IoT device that
> syncs data through a mobile app.

## Overview

**Goal**: Discover every API endpoint the Zepp app uses by intercepting its HTTPS traffic, then build tools to extract all health data programmatically.

**Why**: The Zepp/Huami API is undocumented. The official Zepp Health REST API is corporate-only. To access your own data, you need to know:
- What URLs the app calls
- What parameters each endpoint requires
- What the response format is
- How data is encoded (base64 JSON, binary, encrypted)

**What we found**: 44 unique API endpoints, covering heart rate, sleep, stress, training load, and more.

---

## Methods We Tried

We explored three different approaches to intercepting the Zepp app's HTTPS traffic. Here's what happened with each, and why.

### Method 1: Android Emulator + mitmproxy (Attempted, Abandoned)

**Concept**: Run the Zepp app in an Android emulator, install mitmproxy's CA certificate in the system trust store, and route all traffic through mitmproxy.

**What we tried**:
1. Created an Android 11 (API 30) emulator with "Google APIs" in Android Studio
2. Installed mitmproxy on WSL, generated certificates
3. Ran `adb root` and `adb disable-verity`
4. Tried to `adb remount` to make `/system` writable

**Problems encountered**:
- `adb remount` kept failing with "Read-only file system" even after disabling verity
- The emulator needed to be launched from command line with `-writable-system` flag:
  ```bash
  emulator -avd <name> -writable-system -no-snapshot-load
  ```
- After fixing that, the emulator hung during reboots required by `adb remount`
- Closing the emulator during reboot corrupted the overlayfs state
- Snapshots conflicted with `-writable-system`, requiring `-no-snapshot-load` or `-wipe-data`
- Even when `adb remount` finally succeeded, the `mv` command to install the cert still reported "Read-only file system"

**Lesson learned**: The Android emulator approach is theoretically sound but fragile in practice. The sequence of verity disable -> reboot -> remount -> reboot -> overlayfs activation must complete without interruption. If anything goes wrong (emulator crash, closed during reboot), you often need to wipe and start over.

**When this method works best**: On Linux with a native Android emulator (not WSL), or using a physical rooted Android device.

---

### Method 2: HTTP Toolkit (Attempted, Abandoned)

**Concept**: HTTP Toolkit is a GUI tool for intercepting HTTPS traffic with built-in Android integration.

**What we tried**:
1. Installed HTTP Toolkit on Windows
2. Connected it to intercept traffic

**Problem**: HTTP Toolkit required a paid premium subscription to export captured traffic data. The free version only shows live traffic in the GUI with no export.

**Lesson learned**: HTTP Toolkit is excellent for quick visual inspection of traffic, but not suitable for bulk API mapping without a license.

---

### Method 3: iPhone + mitmdump on Windows (What Actually Worked)

**Concept**: Run `mitmdump` directly on Windows, configure the iPhone's WiFi proxy to point at it, install the mitmproxy CA certificate on the iPhone, and capture all Zepp app traffic to a file.

**Why this worked**: No rooting, no emulator, no fragile system partition modifications. Just a proxy and a trusted certificate.

#### Step-by-step

**1. Install mitmproxy on Windows**
```powershell
pip install mitmproxy
```

**2. Start mitmdump with full detail logging**
```powershell
mitmdump --set flow_detail=4 | Out-File -Encoding utf8 zepp_api_dump.txt
```
- `flow_detail=4` captures full request/response headers AND bodies
- `Out-File -Encoding utf8` handles Unicode characters in responses

**3. Install the mitmproxy CA certificate on iPhone**
- On the iPhone, open Safari and go to `http://mitm.it`
- Download the iOS certificate profile
- Go to Settings -> General -> VPN & Device Management -> install the profile
- Go to Settings -> General -> About -> Certificate Trust Settings -> enable full trust for mitmproxy

**4. Configure iPhone WiFi proxy**
- Settings -> WiFi -> tap the (i) on your connected network
- Configure Proxy -> Manual
- Server: your Windows PC's local IP (e.g., `192.168.0.166`)
- Port: `8080`

**What's happening under the hood**: When you configure a proxy on the iPhone, every HTTP/HTTPS request the phone makes gets routed to your PC first. Your PC (running mitmdump) intercepts the encrypted connection, decrypts it using the trusted CA certificate, logs the full content, then re-encrypts and forwards it to the real server. The response comes back the same way. The Zepp app has no idea this is happening because it trusts the mitmproxy certificate.

**5. Use the Zepp app normally**
- Open the Zepp app on iPhone
- Navigate through every screen: Home, Sleep, Heart Rate, HRV, Stress, Workouts, etc.
- Each screen visit triggers API calls that mitmdump captures

**6. Stop capture**
- Press Ctrl+C in the PowerShell window
- Remove the proxy from iPhone WiFi settings
- Optionally remove the mitmproxy certificate from iPhone trust settings

**Result**: A 5.5MB text file containing every API request and response the Zepp app made.

---

## Parsing the Captured Traffic

The raw dump file is thousands of lines of HTTP traffic. We wrote a Python script (`parse_traffic.py`, included in `examples/`) to automatically:
- Identify unique API endpoints
- Extract methods, hosts, query parameters
- Categorize endpoints by function
- Generate a Markdown report and JSON file

```bash
python examples/parse_traffic.py zepp_api_dump.txt --output api_map.json
```

**Result**: 44 unique API endpoints discovered across Health Data, Events, Sport/Workout, User Data, and Device categories.

---

## The Complete API Map

See [api-reference.md](api-reference.md) for the full, structured API documentation including:
- All endpoints with parameters and example responses
- Data encoding details (base64 JSON, binary HR, stress JSON-in-JSON)
- Authentication requirements
- Timestamp format reference
- Error handling guide

### Summary of Data Sources

| Source | Endpoint | Data |
|--------|----------|------|
| Band Data | `/v1/data/band_data.json` | Minute-by-minute HR, sleep stages, steps, activity |
| Events v2 | `/v2/users/me/events` | Training load (ATL/CTL/TSB), TRIMP, recovery HR, blood pressure |
| Events v1 | `/users/{id}/events` | Stress (5-min intervals), blood pressure |
| Sport Stats | `/v2/watch/users/{id}/WatchSportStatistics/*` | Daily sport load, VO2 max |
| Sport History | `/v1/sport/run/history.json` | Workout list |
| User/Device | `/users/-/profile`, `/device/settings/meta` | Profile, device config |

---

## What About HRV, SpO2, and Respiratory Rate?

After exhaustive analysis of the captured traffic:

**HRV (Heart Rate Variability)**:
- No dedicated HRV API endpoint exists
- HRV is likely derived client-side from continuous heart rate data during sleep
- The `slp.rhr` field (resting heart rate) in band_data is the closest server-side metric
- Stress data (`all_day_stress`) IS derived from HRV, so stress values are an inverse proxy

**SpO2 (Blood Oxygen)**:
- Not found in our capture. Community projects mention `eventType=blood_oxygen`
- May require tapping the specific SpO2 screen during capture, or may not be available for all devices

**Respiratory Rate**:
- Not found as a separate endpoint
- May be embedded in sleep data or not synced to the cloud

---

## Key Technical Discoveries

### Three Data Encoding Formats

1. **Base64 JSON**: The `summary` field is base64-encoded JSON. Decode with:
   ```python
   json.loads(base64.b64decode(raw_string))
   ```

2. **Base64 Binary**: The `data_hr` field is 1440 raw bytes (one per minute). Each byte is a BPM reading. Values of 0 or 254+ mean no reading.

3. **JSON String in JSON**: The stress `data` field is a string containing a JSON array. Must be parsed with a second `json.loads()` call.

### Sleep Crosses Midnight

Sleep data in `band_data` is assigned to the date you fell asleep, not the date you woke up. To get a full night's sleep that started at 11pm Feb 5 and ended at 7am Feb 6, you need to query Feb 5's data.

### The `appPlatform` Header Controls Encryption

Using `appPlatform: web` returns readable JSON. Using `appPlatform: ios_phone` with `x-hm-ekv: 1` returns encrypted binary responses. Always use `web` for programmatic access.

### Confirmed Working Data (from a real extraction)

| Metric | Example Value |
|--------|--------------|
| Steps | 6,548 |
| Distance | 4,644m |
| Calories | 1,247 |
| HR readings | 1,419 valid (of 1,440 min) |
| HR range | 60-147 bpm |
| Avg HR | 88 bpm |
| Stress avg | 43 (max 67, min 5) |
| Stress readings | 143 five-minute intervals |
| Training load | 20 days of ATL/CTL/TSB history |
| Sport load (day) | 56 |
| Sport load (week) | 379 (optimal: 330-735) |

---

## The Challenge: HTTPS Encryption

The Zepp app talks to its servers over HTTPS:

```
Zepp App <--[encrypted tunnel]--> Zepp Server
```

We can't just capture packets with Wireshark because the traffic is encrypted. We need to become a trusted intermediary:

```
Zepp App <--[decrypt]--> mitmproxy <--[re-encrypt]--> Zepp Server
                              ^
                         We read everything here
```

For this to work, the Zepp app must **trust mitmproxy's certificate**.

---

## Common Issues and Solutions

### `adb remount` fails with "Read-only file system"

**Cause**: Emulator wasn't launched with `-writable-system`

**Fix**: Close emulator, relaunch from command line:
```bash
emulator -avd <name> -writable-system -no-snapshot-load
adb root && adb disable-verity && adb reboot
# Wait for FULL reboot
adb root && adb remount
```

### Emulator hangs during reboot

**Cause**: Overlayfs activation or verity changes require full reboot cycle

**Fix**: Wait 2-3 minutes. If truly stuck:
```bash
emulator -avd <name> -writable-system -wipe-data
```

### `mitm.it` doesn't load on iPhone

**Cause**: Proxy isn't configured correctly, or mitmdump isn't running

**Fix**: Verify mitmdump is running on port 8080, verify proxy settings point to correct IP

### `UnicodeEncodeError` when saving mitmdump output

**Cause**: PowerShell's default encoding can't handle some response characters

**Fix**: Pipe through `Out-File -Encoding utf8`:
```powershell
mitmdump --set flow_detail=4 | Out-File -Encoding utf8 output.txt
```

### API returns 401 Unauthorized

**Cause**: Token expired (tokens last a few weeks)

**Fix**: Log in again at `https://user.huami.com/privacy/index.html`, extract fresh `apptoken` from browser cookies

### API returns 500 Internal Server Error

**Cause**: Missing required headers

**Fix**: Ensure both `appPlatform` and `appname` headers are included:
```python
headers = {
    "apptoken": TOKEN,
    "appPlatform": "web",
    "appname": "com.xiaomi.hm.health",
}
```

### band_data.json returns encrypted binary instead of JSON

**Cause**: Using `appPlatform: ios_phone` with `x-hm-ekv: 1` header

**Fix**: Use `appPlatform: web` to get plain JSON with base64 fields

---

## Security and Ethics

### What we're doing
- Intercepting our own traffic to understand a protocol
- Accessing our own data that we have a legal right to
- Not bypassing any actual security (we're using valid auth tokens)

### What we're NOT doing
- Attacking someone else's data
- Exploiting a vulnerability
- Bypassing access controls
- Distributing credentials

### Is this legal?
- **Reverse engineering for interoperability**: Protected under US DMCA exemptions and EU Software Directive
- **Accessing your own data**: Explicitly granted under GDPR and CCPA
- **Certificate installation on your own device**: Perfectly legal
- **Publishing API documentation**: Precedent from hundreds of similar projects (Fitbit, Garmin, etc.)

**Bottom line**: Document and share the API reference. Don't share credentials or other people's data.

---

## Applying This to Other IoT Devices

This same methodology works for any device that syncs through a mobile app:

1. **Set up mitmdump** on your PC
2. **Configure your phone's proxy** to route through it
3. **Install the CA certificate** on your phone
4. **Use the app normally** while capturing traffic
5. **Parse the dump** to identify endpoints
6. **Test each endpoint** with a Python script
7. **Document the API** for others

The specific encoding formats will differ (some devices use protobuf, some use msgpack, some use plain JSON), but the interception technique is universal.
