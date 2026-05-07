## CHAPTER 4: SYSTEM DESIGN AND IMPLEMENTATION

### 4.1 System Architecture Design
The architectural design of BuyWise heavily prioritizes low-latency feedback and uncompromised user experience. To achieve this, the system deliberately moves away from traditional synchronous request-response cycles. By architecturally decoupling the heavy lifting of the web scraping modules from the database insertion logic via robust memory buffers, the backend can operate completely asynchronously. When raw data is fetched, it is immediately broadcast directly to the client via WebSockets while simultaneously being written to the database in the background. As a result, the end-user perceives the system as functionally instantaneous. Even if the underlying HTTP scrapes, DOM parsing, and machine learning inferences take several seconds to fully resolve, the UI begins populating with analytical insights and media the exact millisecond the first review is processed. This streaming architecture guarantees that the user is never left staring at a static loading screen, fundamentally transforming the typically slow process of data aggregation into an interactive, highly engaging visual experience.

**Full Data and Input Flow Chart:**

The BuyWise project follows a highly structured architecture to maintain code clarity, modular development, and strict separation of concerns. The project is strategically divided into frontend presentation, backend processing, localized database storage, and external extraction modules:

```text
       [ Consumers / E-commerce Buyers ]
          │                         │
      (Searches)                 (Chats)
          ▼                         ▼
┌───────────────────────────────────────────────┐
│ FRONTEND (Next.js + React)                    │
│ • Intelligence Dashboard                      │
│ • Live Review Feed (Images & Text)            │
│ • Fake Review Analytics Gauges                │
│ • Floating AI Chatbot Interface               │
└───────────────────────────────────────────────┘
          │                         │
   [ API & WebSockets ]      [ POST /api/chat ]
          │                         │
          ▼                         ▼
┌───────────────────────────────────────────────┐
│ BACKEND (Python + FastAPI)                    │
│                                               │
│ ┌────────────────┐         ┌────────────────┐ │
│ │ Scraper Engine │         │ ChatBot Engine │ │
│ │ • Amazon       │         │ • Intent Parser│ │
│ │ • Flipkart     │         │ • Context Agg. │ │
│ └───────┬────────┘         └────────┬───────┘ │
│         │                           │         │
│         ▼                           ▼         │
│ ┌───────────────────────────────────────────┐ │
│ │ NLP Machine Learning Pipeline             │ │
│ │ • Sentiment Classifier (Scikit-learn)     │ │
│ │ • Fake Detection Heuristics               │ │
│ │ • Market Recommendation Engine            │ │
│ └─────────────────────┬─────────────────────┘ │
│                       │                       │
│ ┌─────────────────────▼─────────────────────┐ │
│ │ WebSocket Broadcaster (Live Updates)      │ │
│ └───────────────────────────────────────────┘ │
└───────────────────────┬───────────────────────┘
                        │
                  (Read & Write)
                        ▼
┌───────────────────────────────────────────────┐
│ DATABASE (SQLite + SQLAlchemy)                │
│ • Aggregated Verified Reviews                 │
│ • Normalized Media URLs                       │
│ • Market Statistics Cache                     │
└───────────────────────────────────────────────┘
```

### 4.2 Folder Structure and Project Setup
To ensure long-term maintainability and facilitate rapid development iterations, the project enforces a strict, logical directory hierarchy. The root directory is split cleanly into two primary workspaces, isolating the frontend and backend environments. The `backend` directory contains specialized subfolders: the `scrapers/` module houses the object-oriented Python scripts responsible for platform-specific DOM parsing (such as `amazon.py` and `flipkart.py`). The core data logic resides in files like `database.py` (which handles SQLAlchemy async setup and migrations) and `models.py` (which defines the SQLite schema). The crucial natural language processing algorithms are centralized within `ml_pipeline.py`. Finally, the API routing layer is organized inside the `routers/` directory, exposing cleanly structured endpoints. Conversely, the `frontend` directory is structured around the modern Next.js App Router paradigm. The `app/` directory controls global layouts, page routing, and CSS stylesheets, while the `components/` folder encapsulates all reusable UI elements, including the ChatBot, SVG FakeGauges, and the complex ReviewFeed logic. This clear separation of concerns ensures that frontend developers and backend data engineers can work completely in parallel without encountering merge conflicts or architectural bottlenecks.

### 4.3 Review Aggregation and Scraper System
The core data ingestion engine is built upon a highly extensible, polymorphic `BaseScraper` interface. This architectural pattern ensures that while all scrapers conform to a unified data contract, they can independently implement the bespoke, highly specific logic required to parse wildly different HTML structures across varying platforms. For example, the `AmazonScraper` relies heavily on strict DOM-walking algorithms with rigorously enforced boundary checks; this is necessary to extract text, star ratings, and review images accurately without accidentally traversing out of the review container and contaminating the data with author names from adjacent reviews. In stark contrast, the `FlipkartScraper` faces obfuscated, heavily encrypted CSS class names that change dynamically. To combat this, it utilizes complex, level-5 DOM traversal techniques and regex-based string matching to identify review patterns based on their structural hierarchy rather than relying on unreliable class identifiers. By isolating these fragile, platform-specific parsing rules into separate, modular classes, the overall system remains highly stable; if Amazon changes its website layout, only the Amazon scraper class needs updating, leaving the rest of the robust BuyWise pipeline completely unaffected.

### 4.4 Instant ML Processing System
Because the application demands real-time feedback, the system architecture explicitly forbids any heavy, blocking tasks from stalling the primary API thread. To achieve this, the NLP pipeline is designed around a multi-tiered architecture. The initial pass, responsible for the immediate "instant analysis," relies on highly optimized, purely mathematical heuristic dictionaries written in vanilla Python. This lightweight layer can scan raw text for excessive capitalization, keyword repetition, and overt rating disparities in mere milliseconds, instantly computing an initial sentiment score and flagging potential fake reviews. This allows the WebSocket to immediately push the data to the UI. Behind the scenes, a secondary, resource-intensive `asyncio` background task is triggered. This background pipeline utilizes heavier, state-of-the-art HuggingFace transformer models (such as DistilBERT) to perform a much deeper, context-aware semantic analysis of the reviews. By decoupling the immediate heuristic response from the heavier transformer enrichment process, BuyWise successfully balances the user's demand for instantaneous visual feedback with the rigorous requirement for deep, academically sound machine learning analysis.

### 4.5 Real-Time Event Processing using WebSockets
Traditional REST APIs are fundamentally ill-suited for real-time dashboards, as they require the client to constantly poll the server, wasting bandwidth and introducing artificial latency. To circumvent this, BuyWise heavily leverages the WebSocket protocol. The FastAPI backend employs a dedicated `ConnectionManager` class that holds and maintains a live list of all active client WebSocket connections. Whenever the asynchronous scraper pipeline successfully extracts and the NLP pipeline evaluates a new review, the database layer triggers a flush event. Instantly, the `ConnectionManager` broadcasts this fully formed JSON payload directly down the open WebSocket pipe to the exact client that requested it. On the receiving end, the React frontend utilizes the `ws.onmessage` lifecycle hook to parse the incoming string. Crucially, the React state management uses a JavaScript `Map` keyed by a unique `review.id` to intelligently deduplicate and merge these incoming objects. This highly optimized approach completely prevents React reconciliation errors, stops duplicate DOM nodes from rendering, and ensures a buttery-smooth scrolling experience as the live feed populates right before the user's eyes.

### 4.6 User Interface and Editor Integration
The frontend architecture makes a deliberate, bold departure from standard, heavily utilized component libraries like Bootstrap, Material-UI, or TailwindCSS. Instead, the UI is constructed entirely using a bespoke, "humanly-made" Vanilla CSS architecture. This strategic choice was made to deliver a highly distinct, premium "Notion-meets-Linear" aesthetic that sets the platform apart from generic analytical tools. The design language features deep charcoal backgrounds (utilizing precise hex codes like `#0f0e0e`) offset by vibrant, high-contrast amber accents. The interface extensively employs subtle glassmorphism overlays to provide depth, while the analytical elements—such as the Fake Review Detector—are rendered using pure, mathematically calculated SVG paths rather than pre-rendered images. This approach ensures that the circular progress gauges scale flawlessly across any device resolution, from large 4K desktop monitors to compact mobile screens, without any pixelation or loss of fidelity. This meticulous attention to custom CSS architecture guarantees that the user interface feels incredibly responsive, dynamic, and distinctly tailored to the high-end data intelligence it provides.

---

## CHAPTER 5: CODING FUNCTIONS

### 5.1 Main Application Setup
The initialization and mounting of the Next.js frontend application form the critical foundation of the user experience. The application architecture relies on the modern Next.js App Router, which leverages a persistent global `layout.tsx` file. This global layout is responsible for maintaining the application state that must never unmount during navigation, most notably the Floating Action Button (FAB) that houses the AI Chatbot interface, ensuring it remains accessible to the user at all times. The primary interactive workspace is defined within `page.tsx`, which programmatically controls a highly optimized split-pane grid layout. On the left pane, the user is presented with a persistent search bar and a scrolling live feed of the scraped review cards. On the right pane, the application dynamically mounts the data visualization dashboards—including the sentiment trend graphs and the fake detection SVG gauges. This setup ensures that as WebSocket data streams in, the right-hand analytical dashboard recalculates and re-renders independently of the left-hand scroll feed, resulting in a highly performant interface that never drops frames or stutters during heavy data influx.

### 5.2 Scraper Integration Module
The web scraping infrastructure is the critical data ingestion point for the entire application, and the `backend/scrapers/amazon.py` file represents its most complex implementation. The core function of this module is to execute HTTP requests that successfully masquerade as legitimate human browsers by utilizing the `curl_cffi` library, which generates highly realistic, randomized TLS fingerprints that defeat Amazon's strict automated bot-detection algorithms. Once the raw HTML payload is secured, the script executes the `_extract_review_images_amazon(node)` function. This function performs a highly surgical parsing of the Document Object Model (DOM). It traverses specific nodes searching for `img` tags, but applies rigorous regex filtering to ensure the image URLs match known Amazon CDN domains (e.g., `images-na.ssl-images-amazon.com`). Crucially, this function includes hardcoded logic to actively identify and discard the tiny 1x1 pixel tracking images that Amazon secretly embeds within review blocks. By filtering out this noise, the function guarantees that only genuine, user-uploaded, high-resolution product photos are returned and saved to the SQLite database.

### 5.3 Database Management Functions
The integrity and persistence of the scraped intelligence rely heavily on a robust, asynchronous database layer. Within the backend, `models.py` serves as the definitive schema registry, strictly defining the `Review` object model and its precise mapping to the underlying SQLite database tables. The core interaction logic is housed in `database.py`, which is engineered using SQLAlchemy's AsyncIO extensions to prevent database locks when multiple scrapers attempt to write hundreds of reviews simultaneously. A critical coding function within this file is the startup migration sequence. This function acts as a safety net during application boot; it queries the SQLite `pragma` tables to inspect the current schema structure. If it detects that newer columns—such as the JSON-based `images` column added in recent updates—are missing, it safely and automatically executes the necessary `ALTER TABLE` SQL commands. This automated, code-first migration strategy ensures strict forward compatibility, allowing developers to add new features to the schema over time without ever risking catastrophic data loss or requiring users to manually run complex database migration scripts.

### 5.4 ML Prompt Handling and Processing
The analytical core of BuyWise is driven by the `analyze_instant(text, rating)` function, which executes the first pass of the Natural Language Processing (NLP) pipeline. Because this function runs synchronously on the critical path before data is broadcast via WebSockets, it is highly optimized for raw execution speed. It accepts the raw review text and the user-provided star rating as inputs and processes them against heavily tailored linguistic libraries. The code meticulously dissects the text, executing multiple regex patterns to calculate metrics such as the ratio of capitalized letters, the frequency of repeated punctuation (e.g., "!!!!!"), and the density of specific, manipulative keywords. The most critical logic within this function involves calculating the "rating disparity." If the function detects a highly positive 5-star rating, but the textual sentiment analysis returns a strongly negative result, the algorithm flags a severe contradiction. These mathematical penalties are aggregated to compute a final `fake_confidence` percentage score (e.g., "99.4% Genuine" or "Suspicious"). This provides the end-user with a highly accurate, instantly calculated metric assessing the trustworthiness of the specific review.

### 5.5 Event Handling and UI Updates
The bridge between the backend ML pipeline and the frontend visual dashboard is entirely managed by the WebSocket event handling functions written in React. Inside the `useEffect` hooks of the frontend components, the `ws.onmessage` function acts as the primary event listener. When the backend fires a stringified JSON payload containing a newly analyzed review, this function parses the data and triggers the `setReviews` state callback. However, simply appending the new review to an array would quickly lead to UI duplication and catastrophic React reconciliation errors, especially given the asynchronous, sometimes repetitive nature of web scraping. To solve this, the state callback utilizes a sophisticated Javascript `Map` architecture. The incoming review object is forcefully keyed by its unique database `review.id`. By updating the state using this Map, the application guarantees strict, client-side deduplication. If a review ID already exists in the UI, it is intelligently merged or ignored; if it is novel, it is instantly rendered. This critical coding pattern ensures absolute data stability and a flawless user experience, even when the server is pushing hundreds of events per second.
