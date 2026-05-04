# ArcWarden Demo UI

Premium pitch UI (Next.js) for the ArcWarden mission control.

## Run

From `demo-ui/`:

```bash
npm install
npm run dev
```

Open: `http://localhost:3001`

The UI consumes live data from:

- `GET /demo/live` (SSE stream)

You can set another API host with:

```bash
set NEXT_PUBLIC_API_BASE=http://localhost:8000
```

