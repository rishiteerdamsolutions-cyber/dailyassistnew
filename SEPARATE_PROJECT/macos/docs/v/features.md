# Visual Agent & Orchestrator - Features List

The **Visual Agent** acts as the physical "eyes" of the BOL framework. Instead of reading HTML code or interacting with browser APIs (which can be easily detected and blocked by bot-mitigation software), this agent physically captures the pixels on the OS screen and uses Computer Vision to understand the layout.

## Core Features

1. **Hardware-Level Screen Capture**
   - Bypasses browser sandboxes by taking a raw physical screenshot of the entire OS display (using `mss`). 
   - Cannot be detected or blocked by website anti-bot scripts (like Cloudflare or Datadome) because it operates outside the browser.

2. **Agnostic Computer Vision (OCR)**
   - Uses Google's Tesseract OCR engine to read raw pixels and convert them into bounding boxes and coordinates.
   - It does not care if the target is an HTML website, a PDF document, a flash game, or an Excel spreadsheet. If it's visible on the screen, the agent can interact with it.

3. **Full-Chain Autonomous Orchestration**
   - The Orchestrator acts as the central nervous system, connecting the "Eyes" (Visual Agent) directly to the "Hands" (Kinematic Agent).
   - Once a word is visually located, the framework automatically extracts its physical coordinates, calculates a human-like Bezier trajectory, and detaches the user's OS mouse to swoop over and click the element.

4. **Multi-Step Chain Execution**
   - Supports autonomous sequential execution for complex tasks.
   - The agent can accept an array of targets (e.g., `["Login", "Username", "Password", "Submit"]`).
   - For every step in the chain, it physically pauses to allow the UI to react, takes a brand-new screenshot to re-evaluate the screen layout, and executes the next click. This perfectly mimics human sequential processing.

5. **Live Image Feedback Loop**
   - Capable of annotating the raw screen capture (drawing bounding boxes over recognized text) and converting it into a base64 string.
   - This allows remote monitoring and debugging of exactly what the agent "saw" before it made a decision, without saving hundreds of images to the hard drive.
