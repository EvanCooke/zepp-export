# Zepp/Huami Cloud API Reference

> Unofficial API documentation for the Zepp (formerly Huami/Amazfit) cloud platform.
> Reverse-engineered from Zepp iOS app v10.0.6 traffic capture (February 2026).
> Covers Amazfit Helio Strap; likely works for Mi Band, Amazfit GTS/GTR, T-Rex, and other Zepp-connected devices.

---

## Table of Contents

- [Base URLs](#base-urls)
- [Authentication](#authentication)
- [Headers](#headers)
- [Endpoints](#endpoints)
  - [1. Band Data](#1-band-data) - HR, sleep, steps, activity
  - [2. Events API v2](#2-events-api-v2) - Training load, PHN, recovery HR, blood pressure
  - [3. Events API v1](#3-events-api-v1) - Stress, blood pressure (legacy)
  - [4. Watch Sport Statistics](#4-watch-sport-statistics) - Sport load, VO2 max
  - [5. Sport History](#5-sport-history) - Workout list and details
  - [6. User Profile](#6-user-profile) - User info and properties
  - [7. Device](#7-device) - Device settings and config
- [Data Encoding](#data-encoding)
- [Timestamps](#timestamps)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)
- [Known Limitations](#known-limitations)

---

## Base URLs

| Region | Base URL |
|--------|----------|
| Global | `https://api-mifit.huami.com` |
| US | `https://api-mifit-us2.zepp.com` |
| Europe | `https://api-mifit-de2.zepp.com` |

Your region is determined at account creation. US accounts use `api-mifit-us2.zepp.com`.

---

## Authentication

All API requests require an `apptoken` header. Tokens can be obtained by:

1. **Browser cookies**: Log in at `https://user.huami.com/privacy/index.html`, then extract the `apptoken` cookie value
2. **Traffic capture**: Intercept the Zepp app's login flow to capture the token from response headers

Tokens expire after several weeks. A 401 response means the token has expired.

---

## Headers

### Required Headers

```
apptoken: <your_auth_token>
appPlatform: web
appname: com.xiaomi.hm.health
```

### Important Notes

| Header | Value | Effect |
|--------|-------|--------|
| `appPlatform` | `web` | Returns unencrypted JSON with base64 fields. **Use this.** |
| `appPlatform` | `ios_phone` | Returns encrypted binary responses. Requires decryption key. |
| `x-hm-ekv` | `1` | Enables encryption. Do NOT include this header. |

**Always use `appPlatform: web`** for programmatic access. The iOS/Android platform headers trigger response encryption that requires proprietary decryption.

### Optional iOS-style Headers

If an endpoint requires iOS-style auth (some v2 endpoints), use:

```
apptoken: <your_auth_token>
appplatform: ios_phone
appname: com.huami.midong
v: 2.0
timezone: America/Chicago
accept: */*
```

---

## Endpoints

### 1. Band Data

The primary health data endpoint. Returns heart rate, sleep, steps, and activity data.

#### `GET /v1/data/band_data.json`

##### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query_type` | string | Yes | `summary` for aggregates, `detail` for full data including HR timeline |
| `device_type` | string | Yes | Use `android_phone` or `0` |
| `userid` | string | Yes | Your numeric user ID |
| `from_date` | string | Yes | Start date `YYYY-MM-DD` |
| `to_date` | string | Yes | End date `YYYY-MM-DD` |

##### Example Request

```
GET /v1/data/band_data.json?query_type=detail&device_type=android_phone&userid=YOUR_ID&from_date=2026-02-06&to_date=2026-02-06
Host: api-mifit-us2.zepp.com
apptoken: <token>
appPlatform: web
appname: com.xiaomi.hm.health
```

##### Response

```json
{
  "code": 1,
  "message": "success",
  "data": [
    {
      "uid": "YOUR_ID",
      "data_type": 0,
      "date_time": "2026-02-06",
      "source": 10289411,
      "summary": "<base64-encoded JSON string>",
      "data_hr": "<base64-encoded binary>",
      "data": "<base64-encoded binary>",
      "device_id": "<device_id>",
      "uuid": "<uuid>"
    }
  ]
}
```

Returns one object per day in the date range.

##### Decoding `summary`

Base64-decode to get JSON:

```json
{
  "goal": 8000,
  "algv": "2.13.14",
  "stp": {
    "ttl": 6548,
    "dis": 4644,
    "cal": 1247,
    "runCal": 1205,
    "runDist": 3794,
    "rn": 97,
    "wk": 12,
    "conAct": 0,
    "stage": [
      {
        "start": 989,
        "stop": 1000,
        "mode": 3,
        "step": 741,
        "dis": 556,
        "cal": 39
      }
    ]
  },
  "slp": {
    "st": 1770445860,
    "ed": 1770483000,
    "dp": 127,
    "lt": 385,
    "rhr": 57,
    "ss": 77,
    "dt": 106,
    "wk": 1,
    "is": 45,
    "lb": 5,
    "ps": 0,
    "pe": 0,
    "obt": -14,
    "supRem": true,
    "supNap": true,
    "sleepScoreVersion": "1.0.1",
    "sleepVersion": 3,
    "stage": [
      { "start": 1471, "stop": 1478, "mode": 4 },
      { "start": 1479, "stop": 1508, "mode": 5 },
      { "start": 1509, "stop": 1523, "mode": 4 },
      { "start": 1524, "stop": 1540, "mode": 8 }
    ],
    "odd_stage": []
  },
  "hr": {
    "maxHr": { "hr": 158, "ts": 1770422906 }
  },
  "tz": "-21600",
  "sn": "2445B548008062",
  "byteLength": 190,
  "sync": 1770515204
}
```

**Step fields (`stp`)**:

| Field | Type | Description |
|-------|------|-------------|
| `ttl` | int | Total steps |
| `dis` | int | Total distance in meters |
| `cal` | int | Total calories burned |
| `runCal` | int | Calories from running |
| `runDist` | int | Running distance in meters |
| `rn` | int | Running time (minutes) |
| `wk` | int | Walking time (minutes) |
| `conAct` | int | Continuous activity minutes |
| `stage` | array | Activity segments (see below) |

**Activity stage modes**:

| Mode | Activity |
|------|----------|
| 1 | Slow walking |
| 3 | Fast walking |
| 7 | Running/jogging |
| 76 | Light activity |

**Sleep fields (`slp`)**:

| Field | Type | Description |
|-------|------|-------------|
| `st` | int | Sleep start, unix timestamp (seconds) |
| `ed` | int | Sleep end, unix timestamp (seconds) |
| `dp` | int | Deep sleep duration (minutes) |
| `lt` | int | Light sleep duration (minutes) |
| `rhr` | int | Resting heart rate (bpm) |
| `ss` | int | Sleep score (0-100) |
| `dt` | int | Duration (total sleep time?) |
| `wk` | int | Wake count during sleep |
| `is` | int | Initial sleep latency (minutes) |
| `lb` | int | Light-to-bed time |
| `obt` | int | Offset from bed time (minutes) |
| `supRem` | bool | Whether device supports REM detection |
| `supNap` | bool | Whether device supports nap detection |
| `stage` | array | Sleep stages (see below) |
| `odd_stage` | array | Nap/irregular sleep stages |

**Sleep stage modes**:

| Mode | Stage |
|------|-------|
| 4 | Light sleep |
| 5 | Deep sleep |
| 7 | Awake |
| 8 | REM |

Stage `start` and `stop` values are minute-of-day offsets (0 = midnight). Values > 1440 indicate the next day (e.g., 1500 = 1:00 AM next day).

##### Decoding `data_hr`

Base64-decode to get a byte array. Each byte = one minute of heart rate data.

| Index | Time | Description |
|-------|------|-------------|
| 0 | 00:00 | Midnight |
| 60 | 01:00 | 1 AM |
| 720 | 12:00 | Noon |
| 1439 | 23:59 | End of day |

**Values**:
- `0`: No reading
- `1-253`: Heart rate in BPM
- `254-255`: No reading / sensor error

Typical day produces ~1,400 valid readings out of 1,440 possible.

```python
import base64
hr_bytes = base64.b64decode(day["data_hr"])
for i, hr in enumerate(hr_bytes):
    if 0 < hr < 254:
        print(f"{i//60:02d}:{i%60:02d} -> {hr} bpm")
```

##### Decoding `data`

Base64-decode to get binary activity data. Structure is less well-understood. Length is typically 3x the number of minutes (4,320 bytes for a full day = 3 bytes per minute), possibly encoding steps, distance, and calories per minute.

---

### 2. Events API v2

The newer events endpoint. Uses `/me` instead of a user ID in the path.

#### `GET /v2/users/me/events`

##### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `eventType` | string | Yes | Event category (see table) |
| `subType` | string | Yes | Event subcategory (see table) |
| `from` | long | Yes | Start time, unix milliseconds |
| `to` | long | Yes | End time, unix milliseconds |
| `limit` | int | No | Max records to return (default varies, use 200) |

##### Event Types

| eventType | subType | Description | Data returned |
|-----------|---------|-------------|---------------|
| `exertion` | `algo_result` | Training load algorithm results | ATL, CTL, TSB, recovery factor, activities, exercise plan |
| `phn` | `daily_analysis` | Personal Health Number daily | TRIMP, ATL, CTL, TSB |
| `phn` | `training_plan` | Training plan data | Plan configuration |
| `sport` | `recovery_hr` | Post-workout HR recovery | Recovery HR curve |
| `blood_pressure` | `real_data` | BP from device sensor | Systolic, diastolic, timestamp |
| `blood_pressure` | `manually_add_data` | Manually entered BP | Systolic, diastolic, timestamp |
| `EmotionBaseline` | `real_data` | Stress/emotion baseline | Baseline values |
| `DailyHealth` | `summary` | Daily health summary | Steps, calories, goals |

##### Example: Training Load

```
GET /v2/users/me/events?eventType=exertion&subType=algo_result&from=0&to=1771199999000&limit=200
```

```json
{
  "items": [
    {
      "userId": "YOUR_ID",
      "eventType": "exertion",
      "subType": "algo_result",
      "timestamp": 1770336000000,
      "value": {
        "exerciseScore": 74,
        "totalScore": 84,
        "targetScore": 57,
        "completionPercent": 147,
        "recoveryFactor": 2,
        "recoveryFactorID": 2,
        "insightState": 0,
        "atl": 53,
        "ctl": 58,
        "tsb": 5,
        "atlTotal": 73,
        "ctlTotal": 75,
        "tsbTotal": 2,
        "lastUpdateTime": 1770482440533,
        "exercisePlan": {
          "heartRateLower": 131,
          "heartRateUpper": 161,
          "intensity": 1,
          "duration": 38
        },
        "activities": [
          {
            "startTime": 1083,
            "endTime": 1130,
            "currentScore": 39
          }
        ]
      }
    }
  ]
}
```

**Training load fields**:

| Field | Description |
|-------|-------------|
| `atl` | Acute Training Load (recent fatigue, ~7-day weighted) |
| `ctl` | Chronic Training Load (long-term fitness, ~42-day weighted) |
| `tsb` | Training Stress Balance (ctl - atl). Positive = recovered, negative = fatigued |
| `exerciseScore` | Today's exercise contribution |
| `totalScore` | Cumulative score |
| `targetScore` | Recommended daily target |
| `completionPercent` | Score as % of target |
| `recoveryFactor` | Recovery state (0-4, higher = more recovered) |
| `exercisePlan.heartRateLower` | Recommended lower HR for training |
| `exercisePlan.heartRateUpper` | Recommended upper HR for training |
| `exercisePlan.duration` | Recommended workout duration (minutes) |
| `exercisePlan.intensity` | Recommended intensity level |
| `activities[].startTime` | Activity start (minute-of-day) |
| `activities[].endTime` | Activity end (minute-of-day) |
| `activities[].currentScore` | Training load score for this activity |

##### Example: PHN (TRIMP)

```
GET /v2/users/me/events?eventType=phn&subType=daily_analysis&from=0&to=1771199999000&limit=200
```

```json
{
  "items": [
    {
      "userId": "YOUR_ID",
      "eventType": "phn",
      "subType": "daily_analysis",
      "timestamp": 1770336000000,
      "value": {
        "phn_plan_id": 0,
        "timezone_offset": 0,
        "result": {
          "trimp": 74,
          "atl": 53,
          "ctl": 58,
          "tsb": 5
        }
      }
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `trimp` | Training Impulse - total training stress for the day |
| `atl` | Acute Training Load |
| `ctl` | Chronic Training Load |
| `tsb` | Training Stress Balance |

---

### 3. Events API v1

The legacy events endpoint. Uses the user ID in the URL path.

#### `GET /users/{userId}/events`

##### Parameters

Same as v2 (`eventType`, `subType`, `from`, `to`, `limit`).

##### Stress Data

```
GET /users/{userId}/events?eventType=all_day_stress&from=1770336000000&to=1770422399000&limit=200
```

```json
{
  "items": [
    {
      "userId": "YOUR_ID",
      "eventType": "all_day_stress",
      "subType": "all_day_stress",
      "timestamp": 1770357600001,
      "deviceType": "0",
      "deviceSn": "2445B548008062",
      "avgStress": "43",
      "maxStress": "67",
      "minStress": "5",
      "relaxProportion": "30",
      "normalProportion": "58",
      "mediumProportion": "12",
      "highProportion": "0",
      "data": "[{\"time\":1770357600000,\"value\":47},...]"
    }
  ]
}
```

**Stress fields**:

| Field | Type | Description |
|-------|------|-------------|
| `avgStress` | string | Average stress level for the day |
| `maxStress` | string | Maximum stress value |
| `minStress` | string | Minimum stress value |
| `relaxProportion` | string | % of day in "relaxed" zone (1-25) |
| `normalProportion` | string | % of day in "normal" zone (26-50) |
| `mediumProportion` | string | % of day in "medium" zone (51-75) |
| `highProportion` | string | % of day in "high" zone (76-100) |
| `data` | string | JSON array of `{time, value}` pairs at 5-minute intervals |

**Stress zones**:

| Range | Zone | Meaning |
|-------|------|---------|
| 1-25 | Relaxed | Low autonomic stress |
| 26-50 | Normal | Baseline activity |
| 51-75 | Medium | Elevated stress |
| 76-100 | High | High physiological stress |

Stress is derived from Heart Rate Variability (HRV). Lower stress values correspond to higher HRV.

The `data` field is a JSON string (not a JSON object). Parse it separately:

```python
import json
readings = json.loads(item["data"])
for r in readings:
    print(f"{r['time']} -> stress {r['value']}")
```

Timestamps in the `data` array are unix milliseconds, spaced 300,000ms (5 minutes) apart.

##### Blood Pressure (v1)

```
GET /users/{userId}/events?eventType=health_data&subType=blood_pressure&from=FROM_MS&to=TO_MS&limit=2000
```

---

### 4. Watch Sport Statistics

Daily sport load and VO2 max tracking.

#### `GET /v2/watch/users/{userId}/WatchSportStatistics/{metric}`

##### Path Parameters

| Name | Values | Description |
|------|--------|-------------|
| `userId` | numeric ID | Your user ID |
| `metric` | `SPORT_LOAD`, `VO2_MAX` | Metric type |

##### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `startDay` | string | Yes | Start date `YYYY-MM-DD` |
| `endDay` | string | Yes | End date `YYYY-MM-DD` |
| `limit` | int | No | Max records (default 900) |
| `isReverse` | string | No | `true` for newest-first ordering |

##### Example: Sport Load

```
GET /v2/watch/users/{userId}/WatchSportStatistics/SPORT_LOAD?startDay=2026-01-19&endDay=2026-02-15&limit=900&isReverse=true
```

```json
{
  "items": [
    {
      "dayId": "2026-02-06",
      "generatedTime": 1770336000,
      "device_source": 10289411,
      "currnetDayTrainLoad": 56,
      "wtlSum": 379,
      "wtlSumOptimalMin": 330,
      "wtlSumOptimalMax": 735,
      "wtlSumOverreaching": 864,
      "updateTime": 1770437852000
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `currnetDayTrainLoad` | Training load score for this day (note: "currnet" is their typo) |
| `wtlSum` | Weekly Training Load sum |
| `wtlSumOptimalMin` | Lower bound of optimal weekly load |
| `wtlSumOptimalMax` | Upper bound of optimal weekly load |
| `wtlSumOverreaching` | Overreaching threshold |

---

### 5. Sport History

#### `GET /v1/sport/run/history.json`

Returns list of past workouts.

##### Parameters

| Name | Type | Description |
|------|------|-------------|
| `userid` | string | Your user ID |
| `from` | string | Start date |
| `to` | string | End date |

#### `GET /v1/sport/run/detail.json`

Returns detailed data for a single workout (HR trace, GPS points if applicable, pace, etc.).

---

### 6. User Profile

#### `GET /users/-/profile`

Returns user profile information (name, height, weight, birthday, etc.).

#### `GET /users/-/properties`

Returns user properties and preferences.

---

### 7. Device

#### `GET /device/settings/meta`

##### Parameters

| Name | Type | Description |
|------|------|-------------|
| `deviceSources` | string | Device source ID (e.g., `10289411` for Helio Strap) |

Returns device-specific settings and capabilities.

---

## Data Encoding

### Base64-encoded JSON

Fields like `summary` in band_data contain base64-encoded JSON strings:

```python
import base64, json
summary = json.loads(base64.b64decode(raw_summary_string))
```

### Base64-encoded Binary

Fields like `data_hr` and `data` contain base64-encoded binary:

```python
import base64
hr_bytes = base64.b64decode(raw_data_hr_string)
hr_values = list(hr_bytes)  # each byte is a heart rate value
```

### JSON Strings Inside JSON

The stress `data` field is a JSON string containing a JSON array. Parse it as a second step:

```python
import json
stress_readings = json.loads(item["data"])  # item["data"] is a string like "[{...}]"
```

### Encrypted Responses

When using `appPlatform: ios_phone` with `x-hm-ekv: 1`, responses are encrypted binary (`application/octet-stream`). Avoid this by using `appPlatform: web`.

---

## Timestamps

The API uses multiple timestamp formats:

| Context | Format | Example |
|---------|--------|---------|
| Event `timestamp` | Unix milliseconds | `1770336000000` |
| Event `from`/`to` params | Unix milliseconds | `1771199999000` |
| Sleep `st`/`ed` | Unix seconds | `1770445860` |
| HR `maxHr.ts` | Unix seconds | `1770422906` |
| Band data `from_date`/`to_date` | Date string | `2026-02-06` |
| Sport stats `startDay`/`endDay` | Date string | `2026-02-06` |
| Activity stage `start`/`stop` | Minute-of-day | `989` (= 16:29) |
| Sleep stage `start`/`stop` | Minute-of-day from midnight | `1479` (= 24:39 = 00:39 next day) |
| Stress `data[].time` | Unix milliseconds | `1770357600000` |

**Converting minute-of-day**: `hours = value // 60`, `minutes = value % 60`. Values > 1440 span into the next calendar day.

---

## Error Handling

| Status | Code | Meaning |
|--------|------|---------|
| 200 | `{"code": 1}` | Success |
| 200 | `{"items": [...]}` | Success (events API) |
| 200 | `{"items": []}` | Success but no data for the query |
| 401 | - | Token expired. Re-authenticate. |
| 500 | `{"code": -50000}` | Server error. Usually missing required headers (`appPlatform`, `appname`). |

Always check `resp.json().get("code") == 1` for band_data endpoints, and `resp.json().get("items")` for events endpoints.

---

## Rate Limits

No explicit rate limits were observed during testing. However:
- Keep date ranges reasonable (1-30 days per request for band_data)
- The `limit` parameter caps events results (use 200 for most, 2000 for blood_pressure)
- Add a small delay between requests to be respectful

---

## Known Limitations

1. **HRV**: No dedicated endpoint. Resting HR available in `slp.rhr`. Stress data is the best HRV proxy (stress is derived from HRV inversely).

2. **SpO2**: Not found in our capture. Community reports `eventType=blood_oxygen` may work on devices that support it. Needs verification.

3. **Respiratory Rate**: Not found as a separate endpoint. May be embedded in sleep data or computed client-side.

4. **Temperature**: Not found as a cloud endpoint. May stay on-device only.

5. **VO2 Max**: The `WatchSportStatistics/VO2_MAX` endpoint exists but returned empty. May require specific outdoor GPS workout types to generate data.

6. **Token expiry**: Tokens last several weeks but there's no refresh endpoint documented. Re-authenticate when you get a 401.

7. **Sleep date assignment**: Sleep data in band_data is assigned to the date you fell asleep, not the date you woke up. To get a full night's sleep that crosses midnight, you need to query the previous day's date.

8. **Activity `data` binary format**: The 3-bytes-per-minute binary activity data structure is not fully decoded. First byte may be step count, remaining bytes unclear.

---

## Device Source IDs

| Device | Source ID |
|--------|-----------|
| Amazfit Helio Strap | `10289411` |

Other devices will have different source IDs. Check the `source` field in band_data responses.

---

## Changelog

- **2026-02-15**: Initial documentation from Zepp iOS app v10.0.6 traffic capture
- Discovered 44 unique endpoints
- Confirmed 6 data sources for health extraction
- Documented binary encoding for HR timeline and activity data
