# Easy Deployment Guide - Render (FREE)

Your Django hotel scraping API is ready for **FREE** deployment on Render!

## 🚀 **Why Render?**
- ✅ **100% FREE** for small apps
- ✅ **Zero configuration** - just connect and deploy  
- ✅ **Perfect for Django** - handles everything automatically
- ✅ **HTTPS included** - secure by default
- ✅ **Auto-deploys** from GitHub commits

## 📋 **5-Minute Deployment Steps:**

### **Step 1: Push to GitHub**
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### **Step 2: Create Render Account**
1. Go to [render.com](https://render.com)
2. Sign up with GitHub (free)

### **Step 3: Deploy**
1. Click "New +" → "Web Service"
2. Connect your GitHub repository `hotels-scrap`
3. Configure:
   - **Name**: `hotels-scrap-api`
   - **Root Directory**: `google_places`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn google_places.wsgi:application`

### **Step 4: Set Environment Variables**
In Render dashboard, add:
```
GOOGLE_PLACES_API_KEY = your-actual-google-api-key
DEBUG = False
```
(SECRET_KEY auto-generates)

### **Step 5: Deploy! 🎉**
Click "Create Web Service" - Render handles everything!

## 🔗 **Your API Will Be Live At:**
```
https://hotels-scrap-api.onrender.com/search/
https://hotels-scrap-api.onrender.com/geocode/
```

## ⚡ **Features You Get:**
- **Free HTTPS** certificate
- **Auto-scaling** 
- **Health monitoring**
- **Logs & metrics**
- **Auto-deploys** on Git push

## � **Free Plan Limits:**
- ✅ 512MB RAM (perfect for your API)
- ✅ Unlimited requests
- ⏰ Sleeps after 15min inactivity (wakes up automatically)

**That's it! Your hotel scraping API will be live and ready to use!** 🚀