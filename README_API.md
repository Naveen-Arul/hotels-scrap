Consolidated Places API

Overview

This repo exposes a single consolidated endpoint for frontend integration:

GET /api/search/

It accepts either an address (preferred) or latitude+longitude, plus a category (single keyword). The backend calls Google Places (server-side) using the environment variable `GOOGLE_PLACES_API_KEY`.

Example request (address + category)

https://hotels-scrap-kisanmitra.onrender.com/api/search/?address=MG%20Road%20Bengaluru&category=restaurants

Query parameters

- address (string) — preferred. Free-form address to geocode and use as search center.
- latitude (float) and longitude (float) — alternative to `address`; both must be provided.
- category (string) — required. Single keyword used exactly as provided (e.g. `restaurants`, `hotels`, `juice`, `fruit`).
- area_size (int, optional) — total search area in meters (default: 5000).
- grid_size (int, optional) — e.g. 3 for a 3x3 grid (default: 3).
- overlap (float, optional) — overlap fraction between grid cells (default: 0.4).

Response shape

The endpoint returns JSON with two top-level keys: `results` (array of place objects) and `metadata` (search params and counts). Each place object contains fields such as `place_id`, `name`, `formatted_address`, `location`, `rating`, `user_ratings_total`, `types`, `phone_number`, `website`, `price_level`, `opening_hours`, `is_open`, etc.

Example (truncated)

{
  "results": [ ... ],
  "metadata": {
    "total_results": 85,
    "search_parameters": {
      "latitude": 12.9746905,
      "longitude": 77.6094613,
      "area_size_km": 5.0,
      "cell_radius_m": 1000,
      "keywords": ["restaurants"],
      "grid_size": 3,
      "overlap": 0.4
    },
    "timestamp": "2025-09-22T16:55:30.630856"
  }
}

API key (where to place it)

Recommended (secure): set the Google Places API key on the server as an environment variable named `GOOGLE_PLACES_API_KEY`.

- Render: set an Environment Variable in your Service > Environment section:
  - Key: `GOOGLE_PLACES_API_KEY`
  - Value: your API key value (e.g., `AIzaSyD_EXAMPLE_1234567890abcdef`)

- Local Windows PowerShell (temporary session):

```powershell
$env:GOOGLE_PLACES_API_KEY = 'AIzaSyD_EXAMPLE_1234567890abcdef'
# Then run your Django dev server in the same session
python manage.py runserver
```

- Windows (persistently for current user):

```powershell
setx GOOGLE_PLACES_API_KEY "AIzaSyD_EXAMPLE_1234567890abcdef"
# Close and reopen PowerShell for the value to persist
```

- .env file (if you use python-dotenv or django-environ):

Create a `.env` file next to `manage.py`:

```
GOOGLE_PLACES_API_KEY=AIzaSyD_EXAMPLE_1234567890abcdef
```

Note: Do NOT commit `.env` to source control.

Passing the API key via query parameters (NOT recommended)

If you want to test quickly from Postman or the browser you can append an `api_key` query param to your request, but this is insecure and not supported by default in the backend (the server reads the env var). Example:

```
https://hotels-scrap-kisanmitra.onrender.com/api/search/?address=MG%20Road%20Bengaluru&category=restaurants&api_key=AIzaSyD_EXAMPLE_1234567890abcdef
```

To accept `api_key` from the request you would need a small change in the server code (`ConsolidatedPlacesAPI.get`) to prefer the incoming `api_key` (not recommended for production). That change looks like:

```python
# inside ConsolidatedPlacesAPI.get
api_key = request.query_params.get('api_key') or os.getenv('GOOGLE_PLACES_API_KEY')
```

But again: passing keys in URLs is insecure (they leak in logs, browser history, and referers).

Example cURL and browser-friendly calls

- cURL (server uses env var):

```bash
curl "https://hotels-scrap-kisanmitra.onrender.com/api/search/?address=MG%20Road%20Bengaluru&category=restaurants"
```

- Browser: open the example URL above.

Example fake API key format

Google API keys usually look like `AIza` followed by a long string. Example (fake):

`AIzaSyD_EXAMPLE_1234567890abcdef`

Security notes

- Keep your API key private.
- Restrict the key in the Google Cloud Console (HTTP referrers or IPs) to limit misuse.
- Prefer server-side calls (current design) so the frontend never sees your Google API key.

If you want, I can:
- Add the small server-side change to accept `api_key` from the query for testing (but with a big warning), or
- Create a short Postman collection / example request JSON and a runnable example using `curl` and PowerShell.

