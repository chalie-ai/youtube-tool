# YouTube Tool

Search YouTube for videos or retrieve trending content. The tool works without an API key (using a fallback scraper), but providing a **YouTube Data API v3 key** greatly improves reliability and search quality.

## Features

- **Search Videos**: Find videos by query
- **Trending Videos**: See what's currently trending on YouTube
- **Two-Tier Strategy**:
  - **Tier 1 (Recommended)**: YouTube Data API v3 (highly reliable, requires free API key)
  - **Tier 2 (Fallback)**: youtube-search-python scraper (no auth, works without API key)

## Getting a Free YouTube Data API v3 Key

Follow these steps to set up a free YouTube Data API v3 key:

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a Project** (top-left menu)
3. Click **NEW PROJECT**
4. Give it a name (e.g., "Chalie YouTube Tool")
5. Click **CREATE**
6. Wait for the project to be created, then select it

### 2. Enable the YouTube Data API v3

1. In the Cloud Console, search for **"YouTube Data API v3"** (use the search bar at the top)
2. Click on **YouTube Data API v3** from the results
3. Click **ENABLE**
4. Wait for it to be enabled

### 3. Create an API Key

1. Go to **Credentials** (left sidebar)
2. Click **+ CREATE CREDENTIALS** (top-left)
3. Select **API Key**
4. A popup will show your new API key
5. Copy the key to your clipboard

### 4. Configure the Key in Chalie

1. Open Chalie in your browser (usually http://localhost:8081)
2. Go to **Brain Admin** → **Tools** (or the tools configuration page)
3. Find **YouTube** in the tools list
4. Click to configure it
5. Paste your API key into the **YOUTUBE_API_KEY** field
6. Save

That's it! The YouTube tool will now use the API for much faster, more reliable results.

## API Quota

- **Free Tier**: 10,000 quota units per day
- **Search**: ~100 units per search (search + video stats)
- **Trending**: ~1 unit per request
- **Effective Limit**: ~99 searches or 10,000 trending requests per day

For most users, the free tier is more than sufficient. If you need more, you can upgrade to a paid plan in Google Cloud Console.

## Fallback Behavior

If the API key is not configured or the API fails:
- The tool automatically falls back to the **youtube-search-python** scraper
- No errors will be shown to the user — it just works with slightly less data
- This ensures Chalie always returns results, with or without an API key

## Troubleshooting

### "API key not valid" Error

- Double-check that your API key is copied correctly (no extra spaces)
- Make sure the YouTube Data API v3 is **enabled** in your Google Cloud project

### Getting No Results

- Try a different search query (some queries return no results on YouTube)
- If using the fallback scraper, YouTube may have updated its HTML — a tool update may be needed
- Check that your internet connection is stable

### Quota Exceeded

- You've hit the 10,000 unit daily limit
- Quota resets at midnight UTC
- If you consistently need more, upgrade your Google Cloud plan (costs vary)
