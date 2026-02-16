# zepp-export

**Your health data. Your rules.**

Open-source Python library and tools for accessing your Amazfit/Zepp health data. No official API needed -- we reverse-engineered the Zepp Cloud API so you don't have to.

## What data can you access?

| Metric | Resolution | Source |
|--------|-----------|--------|
| Heart Rate | Minute-by-minute (1440/day) | Band Data API |
| Sleep Stages | Light, Deep, REM, Awake segments | Band Data API |
| Sleep Score | Nightly score (0-100) + resting HR | Band Data API |
| Steps | Daily total + activity segments | Band Data API |
| Stress | 5-minute intervals (1-100 scale) | Events API v1 |
| Training Load | ATL, CTL, TSB (daily) | Events API v2 |
| TRIMP | Training Impulse (daily) | Events API v2 |
| Sport Load | Daily + weekly with optimal ranges | Sport Statistics API |
| VO2 Max | Per qualifying workout | Sport Statistics API |

**Confirmed working** with Amazfit Helio Strap. Likely compatible with Mi Band, Amazfit GTS/GTR, T-Rex, and other Zepp-connected devices.

## Quick Start

### 1. Get your auth token

1. Go to [user.huami.com/privacy/index.html](https://user.huami.com/privacy/index.html)
2. Log in with your Zepp/Amazfit account
3. Open browser DevTools (F12) -> Application -> Cookies
4. Copy the `apptoken` value

Your user ID is visible in the Zepp app under Profile, or in any API response.

### 2. Set up

```bash
git clone https://github.com/evankp/zepp-export.git
cd zepp-export
pip install -e .

# Create your .env file
cp .env.example .env
# Edit .env with your token and user ID
```

### 3. Use it

```python
from zepp_export import ZeppClient

client = ZeppClient(
    token="your_token_here",
    user_id="your_user_id",
)

# Get today's heart rate (minute-by-minute)
hr = client.get_heart_rate("2026-02-06")
print(f"Got {len(hr)} readings")
print(f"First: {hr[0]['time']} -> {hr[0]['bpm']} bpm")

# Get sleep data (automatically handles midnight crossover)
sleep = client.get_sleep("2026-02-06")
print(f"Score: {sleep['sleep_score']}, Deep: {sleep['deep_minutes']} min")

# Get stress data
stress = client.get_stress("2026-02-06", "2026-02-06")
print(f"Avg stress: {stress[0]['avg_stress']}")

# Get training load (ATL/CTL/TSB)
training = client.get_training_load("2026-02-01", "2026-02-06")
latest = training[-1]
print(f"ATL={latest['atl']} CTL={latest['ctl']} TSB={latest['tsb']}")
```

Or run the example script:

```bash
python examples/pull_all_health_data.py 2026-02-06
```

## Authentication

Tokens are resolved in this order (most explicit wins):

1. **Environment variables**: `ZEPP_TOKEN`, `ZEPP_USER_ID` (best for CI/Docker)
2. **`.env` file**: in the current directory (best for development)
3. **`~/.zepp-export/config`**: global config (set by `zepp_export login`, coming in v0.2)

Tokens expire after several weeks. If you get a `ZeppAuthError`, refresh your token from [user.huami.com](https://user.huami.com/privacy/index.html).

## API Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `get_band_data(date)` | Full daily data (HR, sleep, steps) | dict |
| `get_heart_rate(date)` | Minute-by-minute HR | list of `{minute, time, bpm}` |
| `get_sleep(date)` | Sleep stages, score, resting HR | dict |
| `get_steps(date)` | Steps, distance, calories, activity | dict |
| `get_stress(from, to)` | 5-min stress readings + zones | list of daily records |
| `get_training_load(from, to)` | ATL, CTL, TSB, recovery | list of daily records |
| `get_phn(from, to)` | TRIMP daily values | list of daily records |
| `get_sport_load(from, to)` | Daily/weekly sport load | list of daily records |
| `get_vo2_max(from, to)` | VO2 Max estimates | list of records |

All dates use `YYYY-MM-DD` format. All methods return plain Python dicts and lists.

### Sleep across midnight

`get_sleep(date)` automatically fetches the previous day's data too, because sleep sessions that start before midnight are stored on the previous day's record. This means 2x the API calls compared to other methods. For bulk operations, use `get_band_data()` directly.

### Error handling

```python
from zepp_export import ZeppClient, ZeppAuthError, ZeppAPIError

try:
    hr = client.get_heart_rate("2026-02-06")
except ZeppAuthError:
    print("Token expired -- refresh it")
except ZeppAPIError as e:
    print(f"API error: {e} (status: {e.status_code})")
```

## Region Configuration

| Region | Base URL |
|--------|----------|
| US (default) | `https://api-mifit-us2.zepp.com` |
| Global | `https://api-mifit.huami.com` |
| Europe | `https://api-mifit-de2.zepp.com` |

```python
client = ZeppClient(
    token="...",
    user_id="...",
    base_url="https://api-mifit-de2.zepp.com",  # Europe
)
```

Or set `ZEPP_BASE_URL` in your `.env`.

## Documentation

- **[API Reference](docs/api-reference.md)** -- Complete endpoint documentation with parameters, responses, and encoding details
- **[Mapping Guide](docs/mapping-guide.md)** -- How we reverse-engineered the API (methodology that works for any IoT device)

## How was this built?

We intercepted the Zepp iOS app's HTTPS traffic using `mitmdump`, captured 44 unique API endpoints, decoded three different data encoding formats (base64 JSON, base64 binary, JSON-in-JSON), and documented everything. The full story is in the [Mapping Guide](docs/mapping-guide.md).

## Supported Devices

**Confirmed**: Amazfit Helio Strap

**Likely compatible** (same Zepp/Huami cloud API):
- Mi Band 5/6/7/8
- Amazfit GTS/GTR series
- Amazfit T-Rex series
- Amazfit Bip series
- Any device using the Zepp app

If you test with a different device, please open an issue to confirm compatibility.

## Running Tests

```bash
pip install pytest
pytest tests/
```

## Roadmap

- **v0.1** (current): Python library with all data endpoints
- **v0.2**: CLI tool (`python -m zepp_export pull`), CSV export, guided login
- **v0.3**: Local API server, Apple Health XML export, personal dashboard

## Contributing

Contributions welcome! Especially:
- Testing with different Amazfit/Mi Band devices
- Discovering new endpoints (SpO2, respiratory rate, temperature)
- Export format implementations

## License

MIT -- see [LICENSE](LICENSE).

---

*Built by reverse engineering the Zepp Cloud API. Not affiliated with Zepp Health, Huami, or Amazfit.*
