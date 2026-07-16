# Pardha Dashboard Lite

React, Vite, and Tailwind dashboard for the Pardha FastAPI kernel.

```bash
# Terminal 1, from pardha-core
uvicorn app.main:app --reload

# Terminal 2, from pardha-core/dashboard
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` requests to FastAPI on `http://localhost:8000`.
