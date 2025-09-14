# 🏨 Hotels Scraping API

A Django-based REST API for scraping hotel and accommodation data from Google Places API with an interactive map interface.

## ✨ Features

- 🔍 **Hotel Search** - Find hotels by location with customizable search radius
- 🗺️ **Interactive Map** - Visual map interface with search results display
- 📍 **Geocoding** - Convert addresses to coordinates using Google Places API
- 🌐 **CORS Enabled** - Ready for frontend integration
- 🚀 **Deployment Ready** - Configured for Render, Heroku, and other platforms
- 📱 **Responsive UI** - Mobile-friendly map interface

## 🛠️ Tech Stack

- **Backend**: Django 5.2.5 + Django REST Framework
- **Frontend**: HTML5, CSS3, JavaScript with Leaflet.js maps
- **API**: Google Places API integration
- **Deployment**: Gunicorn + WhiteNoise for static files

## 📁 Project Structure

```
google_places/
├── manage.py              # Django management script
├── settings.py            # Django configuration
├── urls.py               # URL routing
├── views.py              # API endpoints logic
├── wsgi.py               # WSGI application
├── hotel_map.html        # Interactive map interface
├── requirements.txt      # Python dependencies
├── Procfile             # For Heroku/Render deployment
├── render.yaml          # Render platform configuration
└── DEPLOYMENT.md        # Deployment guide
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Places API key
- Virtual environment (recommended)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/naveen-kisanmitra/hotels-scrap.git
   cd hotels-scrap/google_places
   ```

2. **Create virtual environment**
   ```bash
   python -m venv agrointel
   agrointel\Scripts\activate  # Windows
   # or
   source agrointel/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Create .env file
   GOOGLE_PLACES_API_KEY=your-google-places-api-key-here
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver 8001
   ```

6. **Access the application**
   - API Base: `http://127.0.0.1:8001/`
   - Interactive Map: Open `hotel_map.html` in browser

## 📡 API Endpoints

### 🔍 Hotel Search
```http
GET /search/?latitude={lat}&longitude={lng}&area_size={size}&grid_size={grid}&overlap={overlap}
```

**Parameters:**
- `latitude` (required): Search center latitude
- `longitude` (required): Search center longitude  
- `area_size` (optional): Search radius in meters (default: 5000)
- `grid_size` (optional): Grid size for comprehensive search (default: 3)
- `overlap` (optional): Grid overlap factor (default: 0.5)

**Response:**
```json
{
  "results": [
    {
      "place_id": "ChIJ...",
      "name": "Hotel Name",
      "formatted_address": "123 Main St, City",
      "location": {
        "latitude": 40.7128,
        "longitude": -74.0060
      },
      "rating": 4.5,
      "user_ratings_total": 1250,
      "types": ["lodging", "establishment"],
      "phone_number": "+1-555-0123",
      "website": "https://hotel.com",
      "price_level": 3,
      "business_status": "OPERATIONAL"
    }
  ]
}
```

### 📍 Geocoding
```http
GET /geocode/?address={address}
```

**Parameters:**
- `address` (required): Address to geocode

**Response:**
```json
{
  "results": [
    {
      "formatted_address": "New York, NY, USA",
      "location": {
        "latitude": 40.7128,
        "longitude": -74.0060
      }
    }
  ]
}
```

## 🌐 Frontend Integration

The project includes a complete interactive map interface (`hotel_map.html`) featuring:

- 🗺️ **Leaflet.js Map** - Interactive map with zoom and pan
- 🔍 **Search Interface** - Location input with category selection
- 📊 **Results Display** - Detailed hotel information with filtering
- 📱 **Responsive Design** - Works on desktop and mobile
- ⚡ **Real-time Loading** - Progress indicators and status updates

### Usage
1. Open `hotel_map.html` in your browser
2. Enter a location (e.g., "New York", "Times Square")
3. Select category (Hotels, Restaurants, etc.)
4. Click "Search" to find places
5. View results on map and in detailed list

## 🚀 Deployment

### Render (Recommended)
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Set environment variables:
   - `GOOGLE_PLACES_API_KEY`
   - `DEBUG=False`
   - `SECRET_KEY` (auto-generated)
4. Deploy automatically with `render.yaml`

**Environment Variables for Production:**
```env
GOOGLE_PLACES_API_KEY=your-actual-google-api-key
DEBUG=False
ALLOWED_HOSTS=your-domain.onrender.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## 🔧 Configuration

### Django Settings
- **CORS**: Configured for development (localhost:3000, localhost:5500) and production
- **Static Files**: WhiteNoise for serving static files in production
- **Security**: Production-ready security headers when DEBUG=False
- **API**: Django REST Framework with proper error handling

### Google Places API
- Requires valid Google Cloud Platform account
- Enable Places API and Geocoding API
- Set up billing (free tier available)
- Generate API key with proper restrictions

## 🧪 Testing

```bash
# Test the API endpoints
curl "http://127.0.0.1:8001/search/?latitude=40.7128&longitude=-74.0060"
curl "http://127.0.0.1:8001/geocode/?address=Times Square, New York"

# Run Django checks
python manage.py check
python manage.py check --deploy  # Production readiness
```

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

If you encounter any issues:
1. Check the [DEPLOYMENT.md](DEPLOYMENT.md) guide
2. Verify your Google Places API key and quotas
3. Check server logs for detailed error messages
4. Open an issue on GitHub

## 🚀 Live Demo

- **API**: `https://your-app.onrender.com/`
- **Frontend**: Open `hotel_map.html` with any web server

---

**Built with ❤️ for efficient hotel data scraping and location services**