# 🚀 Deployment Guide for Render.com

This guide explains how to deploy your Bill Extraction API to Render using the Docker setup we've prepared.

## Prerequisites

1.  A [GitHub](https://github.com/) account.
2.  A [Render](https://render.com/) account.
3.  Your **Gemini API Key**.

---

## Step 1: Push Code to GitHub

1.  Create a new repository on GitHub (e.g., `bill-extractor-api`).
2.  Push your local code to this repository:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/bill-extractor-api.git
git push -u origin main
```

*(Make sure `.env` is in your `.gitignore` so you don't push your API keys!)*

---

## Step 2: Deploy on Render

### Option A: Automatic Deployment (Recommended)

Since we have a `render.yaml` file, you can use "Blueprints":

1.  Go to the [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** -> **Blueprint**.
3.  Connect your GitHub repository.
4.  Render will read `render.yaml` and set up the service.
5.  **Important:** You will need to manually enter your `GEMINI_API_KEY` when prompted or in the dashboard settings after creation.

### Option B: Manual Setup

1.  Go to the [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** -> **Web Service**.
3.  Connect your GitHub repository.
4.  **Name:** `bill-extraction-api` (or any name).
5.  **Runtime:** Select **Docker**.
6.  **Region:** Choose the one closest to you (e.g., Oregon, Frankfurt).
7.  **Instance Type:** **Free** (512 MB RAM).
8.  **Environment Variables:**
    Scroll down to "Environment Variables" and add:
    *   `GEMINI_API_KEY`: `Your_Actual_Gemini_API_Key`
    *   `LLM_PROVIDER`: `gemini`
    *   `API_PORT`: `8000`

9.  Click **Create Web Service**.

---

## Step 3: Verify Deployment

1.  Render will start building your Docker image. This might take a few minutes.
2.  Watch the logs. You should eventually see:
    ```
    INFO:     Uvicorn running on http://0.0.0.0:8000
    ```
3.  Once deployed, Render will give you a URL (e.g., `https://bill-extraction-api.onrender.com`).
4.  Visit `https://YOUR_APP_URL/docs` to see the Swagger UI and test the API.

---

## Troubleshooting

*   **Build Failed?** Check the logs. Ensure `requirements.txt` is correct.
*   **App Crashing?** Check if `GEMINI_API_KEY` is set correctly in the Environment Variables.
*   **Memory Issues?** The Free tier has 512MB. Our pure Gemini Vision approach is very lightweight, so this should not be an issue.
