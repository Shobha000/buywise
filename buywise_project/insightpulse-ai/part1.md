# Project Report: BuyWise — Real-Time Review Intelligence

## TABLE OF CONTENTS
- [Declaration](#declaration)
- [Certificate](#certificate)
- [Acknowledgement](#acknowledgement)
- [Abstract](#abstract)
- [List of Abbreviations](#list-of-abbreviations)
- [Chapter 1: Introduction](#chapter-1-introduction)
  - [1.1 Prologue](#11-prologue)
  - [1.2 Background and Motivation](#12-background-and-motivation)
  - [1.3 Problem Statement](#13-problem-statement)
  - [1.4 Objectives and Research Methodology](#14-objectives-and-research-methodology)
  - [1.5 Project Organization](#15-project-organization)
- [Chapter 2: System Overview](#chapter-2-system-overview)
  - [2.1 Project Description](#21-project-description)
  - [2.2 Technologies Used](#22-technologies-used)
  - [2.3 System Architecture](#23-system-architecture)
  - [2.4 System Workflow](#24-system-workflow)
- [Chapter 3: Hardware and Software Requirements](#chapter-3-hardware-and-software-requirements)
  - [3.1 Hardware Requirements](#31-hardware-requirements)
  - [3.2 Software Requirements](#32-software-requirements)
- [Chapter 4: System Design and Implementation](#chapter-4-system-design-and-implementation)
  - [4.1 System Architecture Design](#41-system-architecture-design)
  - [4.2 Folder Structure and Project Setup](#42-folder-structure-and-project-setup)
  - [4.3 Review Aggregation and Scraper System](#43-review-aggregation-and-scraper-system)
  - [4.4 Instant ML Processing System](#44-instant-ml-processing-system)
  - [4.5 Real-Time Event Processing using WebSockets](#45-real-time-event-processing-using-websockets)
  - [4.6 User Interface and Editor Integration](#46-user-interface-and-editor-integration)
- [Chapter 5: Coding Functions](#chapter-5-coding-functions)
  - [5.1 Main Application Setup](#51-main-application-setup)
  - [5.2 Scraper Integration Module](#52-scraper-integration-module)
  - [5.3 Database Management Functions](#53-database-management-functions)
  - [5.4 ML Prompt Handling and Processing](#54-ml-prompt-handling-and-processing)
  - [5.5 Event Handling and UI Updates](#55-event-handling-and-ui-updates)
- [Chapter 6: Working Code and Implementation](#chapter-6-working-code-and-implementation)
- [Chapter 7: Testing Strategies](#chapter-7-testing-strategies)
  - [7.1 Unit Testing](#71-unit-testing)
  - [7.2 Integration Testing](#72-integration-testing)
  - [7.3 Performance Testing](#73-performance-testing)
- [Chapter 8: Limitations](#chapter-8-limitations)
- [Chapter 9: Results and Discussion](#chapter-9-results-and-discussion)
- [Chapter 10: Conclusion and Future Enhancements](#chapter-10-conclusion-and-future-enhancements)
  - [Conclusion](#conclusion)
  - [Future Enhancements](#future-enhancements)
- [References](#references)

*(Note: Declaration, Certificate, and Acknowledgement pages should be generated manually with student signatures as per the university template).*

---

## Abstract
E-commerce platforms heavily rely on customer reviews to drive sales; however, the proliferation of fake reviews, review bombing, and disorganized feedback presents a significant challenge for consumers trying to make informed purchasing decisions. To address this, we present **BuyWise**, a real-time review intelligence system designed to autonomously scrape, aggregate, and analyze product reviews from multiple e-commerce sources instantaneously. The system operates on a decoupled client-server architecture, utilizing a FastAPI backend for asynchronous, anti-bot web scraping and a Next.js frontend for dynamic data visualization. As raw reviews and images are extracted, BuyWise employs localized Natural Language Processing (NLP) models to compute sentiment scores, extract relevant product topics, and detect linguistic anomalies indicative of fake or manipulated reviews. To achieve zero-latency user feedback, the architecture bypasses traditional batch-processing by utilizing SQLite for instant data deduplication and WebSockets to stream analyzed reviews directly to the client interface. The resulting platform provides consumers with a transparent, editorial-grade dashboard featuring live analytical gauges and a conversational AI chatbot. BuyWise successfully demonstrates how real-time machine learning and resilient data pipelines can be combined to filter out market noise and fundamentally enhance consumer protection in digital retail environments.

## List of Abbreviations
- **AI**: Artificial Intelligence
- **API**: Application Programming Interface
- **NLP**: Natural Language Processing
- **DOM**: Document Object Model
- **ORM**: Object-Relational Mapping
- **FAB**: Floating Action Button
- **WS**: WebSocket

---

## CHAPTER 1: INTRODUCTION

### 1.1 Prologue
In the fast-paced digital age, online shopping has transitioned from a convenience to an absolute necessity. With this shift, consumers have grown increasingly dependent on crowdsourced feedback—specifically product reviews—to assess the quality, reliability, and value of items before completing a purchase. However, this heavy reliance has inadvertently birthed a massive, deceptive industry centered entirely around manipulated feedback. Bad actors, ranging from automated bots to incentivized human reviewers, routinely post fake reviews to artificially inflate the ratings of subpar products or maliciously deflate the ratings of competitors. This creates a highly distorted marketplace where genuine consumer voices are drowned out by orchestrated campaigns. Consequently, trust in digital retail platforms has severely eroded. BuyWise was conceptualized to directly combat this systemic issue. Designed to act as a digital "ReviewGuard," the platform provides a robust, intelligent layer of verification that intercepts this deceptive noise. By employing advanced machine learning and real-time data aggregation, BuyWise cuts through the clutter to deliver clear, verified signals to the consumer, restoring transparency and ensuring that everyday shoppers can navigate the e-commerce landscape with confidence and clarity.

### 1.2 Background and Motivation
The primary motivation behind the development of BuyWise stems from the escalating difficulty of authenticating user reviews on modern digital storefronts. While massive platforms like Amazon and Flipkart have deployed their own proprietary filtering algorithms, these systems are fundamentally opaque, leaving consumers completely in the dark regarding how reviews are ranked or suppressed. Furthermore, these internal systems are frequently bypassed or heavily gamified by sophisticated sellers who understand how to exploit platform vulnerabilities. As a result, shoppers are forced to spend excessive amounts of time manually reading through comments, attempting to guess which feedback is legitimate. There is a pressing, unfulfilled need for a completely transparent, third-party analytics tool that does not possess the inherent biases of the platforms selling the products. BuyWise was motivated by the desire to build a tool that systematically evaluates the statistical, behavioral, and linguistic properties of reviews. By highlighting suspicious patterns—such as repetitive keyword stuffing, unnatural capitalization, or contradictory rating-to-text ratios—BuyWise warns consumers of potentially fraudulent activity, empowering them with the objective, data-driven insights necessary to make truly informed purchasing decisions in a crowded digital marketplace.

### 1.3 Problem Statement
The central problem this project addresses is the lack of accessible, real-time verification tools for e-commerce product reviews. Specifically, the goal is to design, develop, and deploy a unified, real-time review intelligence platform capable of navigating the complex, highly defended infrastructure of modern retail websites. This platform must be capable of bypassing sophisticated, dynamic anti-scraper blocks to aggregate review data seamlessly across multiple domains without manual user intervention. Once the data is successfully aggregated, the system must apply a localized, high-speed Natural Language Processing (NLP) pipeline to immediately determine the core sentiment, extract relevant product topics, and calculate the authenticity of each individual review. Furthermore, this complex backend processing must be entirely invisible to the user; the system is required to present its findings dynamically and instantaneously through an intuitive, editorial-grade user interface. The ultimate challenge lies in executing this entire pipeline—from data extraction to ML analysis and UI rendering—without the severe latency typically associated with traditional, scheduled batch-processing pipelines, thereby offering consumers immediate protection while they shop.

### 1.4 Objectives and Research Methodology
The development of BuyWise was guided by several core objectives, supported by an agile research methodology. The first objective was **Real-Time Data Aggregation**. This required researching and implementing resilient, asynchronous web scrapers capable of mimicking human browser fingerprints to bypass sophisticated anti-bot protections, ensuring a steady stream of dynamic product reviews. The second objective focused on **Fake Review Detection**. The research here involved analyzing linguistic and statistical markers within large datasets of verified fake reviews to build a robust heuristic model that calculates a mathematically sound "suspicious" confidence score for every extracted comment. The third objective was **Market Sentiment Analysis**, which necessitated the integration of Natural Language Processing libraries to generate automated insights, concise summaries, and accurate topic extractions from raw, unstructured text. The final objective was delivering an **Editorial-Grade UX**. The methodology for this phase involved abandoning standard, rigid component libraries in favor of a bespoke, "Notion-meets-Linear" aesthetic. This included engineering a highly responsive frontend that visualizes the backend data instantly via WebSockets, guaranteeing a seamless, premium user experience.

### 1.5 Project Organization
This project report is systematically structured into ten comprehensive chapters, each detailing a critical phase of the BuyWise platform's lifecycle. Following this introductory chapter, Chapter 2 provides a high-level System Overview, discussing the foundational technologies and the overarching system workflow. Chapter 3 explicitly outlines the Hardware and Software Requirements necessary to deploy and maintain the application. Chapters 4 and 5 form the technical core of the document, delving deeply into the System Design, architectural choices, and the specific Coding Functions that power the backend pipelines and frontend interfaces. Chapter 6 serves as the implementation evidence, showcasing the working code through visual screenshots of the live dashboard. Chapter 7 details the rigorous Testing Strategies employed—including unit, integration, and performance testing—to guarantee system stability. Chapter 8 candidly addresses the current Limitations of the architecture, such as constraints related to IP rate limiting and JavaScript-rendered content. Chapter 9 presents the Results and Discussion, evaluating the project's success against its initial objectives. Finally, Chapter 10 provides the Conclusion and outlines exciting avenues for Future Enhancements.

---

## CHAPTER 2: SYSTEM OVERVIEW

### 2.1 Project Description
BuyWise is a sophisticated, full-stack intelligence application meticulously divided into two primary environments: a high-performance FastAPI backend and a dynamic Next.js React frontend. The backend acts as the central nervous system of the project. It is responsible for managing distributed, asynchronous web scraping tasks, performing rigorous data normalization, executing instant Machine Learning (ML) analysis, and maintaining data integrity through a local database. Crucially, the backend is designed to continuously broadcast these processed events to the frontend via active WebSockets. The frontend serves as the interactive presentation layer, providing users with a highly polished, dark-themed, dashboard-style interface. This interface is not static; it features live feed updates that stream in reviews the moment they are scraped, alongside custom-built, SVG-based analytical gauges that visually represent complex sentiment and authenticity metrics. Additionally, the project features an integrated, floating AI Chatbot assistant that can parse user intents and provide conversational, context-aware summaries of the current product market, making the platform both an analytical tool and a personalized shopping concierge.

### 2.2 Technologies Used
The technology stack for BuyWise was strategically selected to prioritize speed, concurrency, and developer ergonomics. On the **Frontend**, the application leverages Next.js 15 and React 19, utilizing TypeScript for strict type safety and Vanilla CSS to achieve a highly customized, Editorial Amber Theme without the bloat of external styling frameworks. For the **Backend**, Python was chosen for its unparalleled ecosystem in data processing and machine learning. The server is built on FastAPI and runs via the Uvicorn ASGI server, ensuring maximum throughput for asynchronous requests. The **Database** layer relies on SQLite combined with SQLAlchemy's Async ORM, providing a lightweight yet powerful transactional store that prevents locking during heavy concurrent writes. For **Data Scraping**, the project utilizes `curl_cffi` to generate TLS fingerprints that resist advanced bot detection, paired with BeautifulSoup4 for rapid DOM traversal. The **Machine Learning** pipeline integrates HuggingFace `transformers` and Scikit-learn for local, fast-execution heuristic pipelines. Finally, **Real-time Communication** between the isolated backend and frontend environments is achieved seamlessly through native WebSockets.

### 2.3 System Architecture
The underlying architecture of BuyWise follows a highly decoupled, modern client-server model that maximizes scalability and separation of concerns. The flow begins with the **Client (Next.js)**, which takes the user's search queries and immediately establishes a persistent, open WebSocket connection, preparing the UI to receive streamed data. The request is routed to the **Server (FastAPI)**, which acts as a master controller. Instead of blocking the main thread, the server fans out asynchronous scraping tasks to specialized, platform-specific modules designed for targets like Amazon or Flipkart. As raw HTML is retrieved, it enters the **Processing Pipeline**. Here, the scraped Document Object Models (DOMs) are parsed, and the raw text and images are extracted. Crucially, this data is normalized and deduplicated against the SQLite database to ensure only novel information is processed. The unique reviews are then fed through the localized NLP pipeline for sentiment scoring and fake detection. Finally, the **Data Stream** activates: the validated, fully analyzed review objects are simultaneously committed to the database and broadcasted to the Client via the WebSocket channel, triggering an instant, dynamic re-render on the user's screen.

### 2.4 System Workflow
The operational workflow of BuyWise is designed to be entirely transparent to the end-user while executing highly complex background tasks. When a user initiates a search for a product (for example, "Samsung Galaxy S24"), the UI immediately transitions to a loading state and establishes a live WebSocket listener. Simultaneously, the backend triggers its `safe_scrape` protocol. This protocol dispatches HTTP requests using randomized, rotating TLS fingerprints to successfully bypass the target website's automated bot protections. Once the raw HTML is acquired, the specific scraper engine extracts the relevant reviews, star ratings, and associated high-resolution images. A strict database check is performed; if a review text is a duplicate, it is skipped to maintain dataset purity. The novel reviews are then synchronously passed through the NLP functions, which append calculated metadata including the `sentiment` classification, extracted `topics`, and the critical `is_fake` confidence flag. As soon as the analysis completes, the enriched review object is saved to the SQLite database and instantly pushed through the WebSocket to the UI. The frontend catches this payload and dynamically animates the analytical gauges—updating Total Reviews, Sentiment Ratios, and Fake Detection percentages—in true real-time.

---

## CHAPTER 3: HARDWARE AND SOFTWARE REQUIREMENTS

### 3.1 Hardware Requirements
To ensure the seamless operation, development, and deployment of the BuyWise platform, specific hardware thresholds must be met. The system was designed to be relatively lightweight on the frontend but demands moderate computational resources on the backend due to the integration of local machine learning models and asynchronous I/O operations. The minimum required **Processor** is an Intel Core i5 or AMD Ryzen 5 architecture; however, the codebase has been extensively optimized to run natively and highly efficiently on Apple Silicon (M1/M2/M3 chips), leveraging modern ARM architectures for faster execution. Regarding Memory, a minimum of 8 GB of **RAM** is strictly required to prevent bottlenecking during heavy DOM parsing. However, 16 GB of RAM is highly recommended, especially when loading and running localized HuggingFace NLP models concurrently with the ASGI server. The platform requires minimal physical **Storage**, with only 5 GB of available space needed to accommodate the Python virtual environments, Node modules, and the growing SQLite database. Finally, a robust **Network** infrastructure—specifically a highly stable broadband connection—is mandatory, as the platform relies heavily on low-latency, real-time HTTP requests to external e-commerce servers.

### 3.2 Software Requirements
The software ecosystem supporting BuyWise is built entirely on modern, open-source frameworks and strictly defined runtime environments. The application is highly cross-platform and fully supports deployment on any standard **Operating System**, including Windows 10/11, macOS, and major Linux distributions (such as Ubuntu or Alpine for containerized deployment). The core execution relies on two distinct **Runtime Environments**: Node.js (version 18 or higher) is required to compile and serve the Next.js React frontend, while Python (version 3.10 or higher) is strictly required to support the advanced asynchronous features and type hinting utilized extensively throughout the FastAPI backend. Dependency management is handled via industry-standard **Package Managers**; `npm` (Node Package Manager) is used to resolve frontend UI libraries and build tools, whereas `pip` manages the complex web of backend Python dependencies, including Scikit-learn, BeautifulSoup4, and SQLAlchemy. From the end-user perspective, interacting with the BuyWise dashboard requires a modern, JavaScript-enabled **Web Browser** such as Google Chrome, Mozilla Firefox, or Apple Safari, specifically one that fully supports the HTML5 WebSocket API for real-time data streaming.
