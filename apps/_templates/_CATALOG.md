# App Template Catalog

This file is the machine-readable catalog of all available app templates.

**When to read this file:** During template selection (Step 2 of SKILL.md) — read the `pick_when` fields to choose the right template before copying.

---

```yaml
templates:

  - name: flask-basic
    description: "General web app with Python backend logic — forms, pages, dynamic content, custom API endpoints"
    use_cases:
      - "Web form that processes user input"
      - "Multi-page site with dynamic content"
      - "Custom REST API with business logic"
      - "Any app that needs Python backend but no DB or file handling"
      - "Anything not covered by a more specialized template"
    pick_when: "The app needs Python backend logic and doesn't fit a more specific template (no DB, no file uploads, no real-time streaming, no standalone tool)"
    start_command: "python app.py"
    has_backend: true
    has_database: false
    key_features:
      - "Flask routes with Jinja2 templates"
      - "base.html layout with topbar and content area"
      - "dark theme CSS with card/button/grid components"
      - "fetch helper and DOM-ready boilerplate in app.js"
      - "example /api/data endpoint"

  - name: flask-dashboard
    description: "Metrics dashboard with polling data refresh and a line chart"
    use_cases:
      - "System monitoring dashboard"
      - "Business metrics display"
      - "Single chart type with a few metric cards"
      - "Dashboard where polling refresh is sufficient (not real-time)"
      - "psutil-based resource usage viewer"
    pick_when: "The app shows metrics/charts and polling refresh is sufficient — no need for SSE streaming or multiple chart types"
    start_command: "python app.py"
    has_backend: true
    has_database: false
    key_features:
      - "Chart.js line chart loaded from CDN"
      - "Metric cards grid"
      - "/api/data endpoint returning metrics + chart data"
      - "Polling refresh"
      - "psutil-ready for system metrics"

  - name: static-html
    description: "Pure front-end page with no Python backend logic — static data or external APIs"
    use_cases:
      - "D3.js or Plotly visualization from static data"
      - "Single-page view fetching an external API"
      - "Custom SVG or canvas rendering"
      - "Static data display or report page"
      - "Front-end only prototype"
    pick_when: "The app has no Python backend logic — all rendering happens in the browser, data is static or from an external API"
    start_command: "python serve.py"
    has_backend: false
    has_database: false
    key_features:
      - "serve.py minimal Flask static file server"
      - "Automatic <base> tag injection for sub-path routing"
      - "Chart.js pre-wired (D3/Plotly CDN options commented in)"
      - "dark theme matching other templates"
      - "No npm or build step needed"

  - name: utility-spa
    description: "Lightweight single-page tool — input-process-output pattern, no backend needed"
    use_cases:
      - "Calculator or unit converter"
      - "Text transformer or formatter"
      - "Encoding/decoding tool (base64, URL encode, etc.)"
      - "Local data viewer or inspector"
      - "Any tool where all logic runs in the browser"
    pick_when: "The app is an input-process-output tool that runs entirely in the browser with no server-side logic or storage"
    start_command: "python serve.py"
    has_backend: false
    has_database: false
    key_features:
      - "Input textarea + action buttons + output area layout"
      - "serve.py static file server with base tag injection"
      - "Copy-to-clipboard on output"
      - "Pure vanilla JS — no framework or CDN required"
      - "Sample text transformer functions to replace"

  - name: dashboard-realtime
    description: "Real-time dashboard with SSE streaming and multiple chart types (line, bar, doughnut)"
    use_cases:
      - "Live system or process monitoring"
      - "Real-time data feed display"
      - "Dashboard with multiple simultaneous chart types"
      - "Streaming metrics that update every few seconds"
      - "Live log or event viewer"
    pick_when: "The app shows live data that updates in real-time via SSE streaming, or needs multiple chart types (line + bar + doughnut) simultaneously"
    start_command: "python app.py"
    has_backend: true
    has_database: false
    key_features:
      - "Server-Sent Events (SSE) primary channel with polling fallback"
      - "Three Chart.js charts: line (time series), bar, doughnut"
      - "Connection status indicator (connected / reconnecting / error)"
      - "Metric cards with live values"
      - "Charts update in-place (no destroy/recreate flicker)"

  - name: crud-app
    description: "Data management app with SQLite database — create, read, update, delete records"
    use_cases:
      - "Item/record/entry manager"
      - "Simple inventory or task tracker"
      - "Any app that needs to persist and manage structured data"
      - "List + detail + create + edit + delete UI for any model"
      - "Admin-style data tool"
    pick_when: "The app needs to store and manage structured data records in a database (create, read, update, delete)"
    start_command: "python app.py"
    has_backend: true
    has_database: true
    key_features:
      - "SQLite with get_db()/close_db() pattern using flask.g"
      - "Parameterized SQL queries (no f-strings with user input)"
      - "7 routes: list, detail, new, create, edit, update, delete"
      - "Shared form.html for create and edit (item=None / item object)"
      - "Flash messages (success/error categories)"
      - "404 handling for missing items"
      - "Dark-theme data table with badge styles"

  - name: file-tool
    description: "File upload, management, and conversion tool with drag-and-drop UI"
    use_cases:
      - "File upload and download service"
      - "Format conversion tool (csv<->json, txt->json, etc.)"
      - "Document or media processing app"
      - "File manager or organizer"
      - "Any app where users upload files for processing"
    pick_when: "The app's primary purpose is file handling — uploading, downloading, listing, or converting files"
    start_command: "python app.py"
    has_backend: true
    has_database: false
    key_features:
      - "Drag-and-drop dropzone + file picker upload"
      - "File listing as card grid with filename, size, date"
      - "Download and delete endpoints"
      - "Format conversion pipeline (txt->json, csv->json, json->csv, txt->uppercase)"
      - "secure_filename on all endpoints (path traversal protection)"
      - "Toast notifications for upload/convert/delete feedback"
      - "50 MB upload limit"
```
