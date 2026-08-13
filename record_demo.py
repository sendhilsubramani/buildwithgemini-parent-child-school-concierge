import os
import time
import shutil
import subprocess
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = "/home/user/.gemini/antigravity-cli/brain/4e540636-6a5f-4753-844c-b00360097ef0"
TEMP_VIDEO_DIR = "/tmp/playwright_demo_video"
FINAL_MP4_PATH = os.path.join(ARTIFACT_DIR, "parent_child_school_concierge_demo.mp4")

os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

print("Starting Playwright demo video recording...")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    context = browser.new_context(
        record_video_dir=TEMP_VIDEO_DIR,
        record_video_size={"width": 1280, "height": 800},
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()

    print("Navigating to live Cloud Run app...")
    page.goto("https://school-concierge-frontend-153647604547.us-east1.run.app", wait_until="networkidle")
    time.sleep(3)  # Let the dashboard iframes render cleanly

    # --- Prompt 1: Core Feature - Check Health & Pediatric Alerts ---
    prompt1 = "Check Leo's upcoming medical records and annual health checkup alerts"
    print(f"Typing Prompt 1: '{prompt1}'")
    page.type("#input", prompt1, delay=50)
    time.sleep(1)
    page.click("#form button")

    print("Waiting for response to Prompt 1...")
    # Wait until a response bubble appears that isn't '…'
    page.wait_for_function("document.querySelectorAll('#log .msg.agent').length > 0 && !document.querySelector('#log .msg.agent:last-child').textContent.includes('…')", timeout=60000)
    time.sleep(5)  # Showcase rendered A2UI card

    # --- Prompt 2: Richer Feature - Parent Coaching Guidance ---
    prompt2 = "Send parent guidance for Leo to take a break and focus on Math Worksheet #12 with encouraging emojis"
    print(f"Typing Prompt 2: '{prompt2}'")
    page.type("#input", prompt2, delay=40)
    time.sleep(1)
    page.click("#form button")

    print("Waiting for response to Prompt 2...")
    page.wait_for_function("document.querySelectorAll('#log .msg.agent').length > 1 && !document.querySelector('#log .msg.agent:last-child').textContent.includes('…')", timeout=60000)
    time.sleep(5)  # Showcase rendered A2UI card

    # --- Prompt 3: Student Avatar Generation ---
    prompt3 = "Generate an achievement avatar picture for Leo with star emojis and a science fair trophy"
    print(f"Typing Prompt 3: '{prompt3}'")
    page.type("#input", prompt3, delay=40)
    time.sleep(1)
    page.click("#form button")

    print("Waiting for response to Prompt 3...")
    page.wait_for_function("document.querySelectorAll('#log .msg.agent').length > 2 && !document.querySelector('#log .msg.agent:last-child').textContent.includes('…')", timeout=60000)
    time.sleep(6)  # Final hold to view complete dashboard & conversation

    video_path = page.video.path()
    context.close()
    browser.close()

print(f"Playwright video recorded at: {video_path}")

# Convert WEBM to MP4 using ffmpeg
cmd = [
    "ffmpeg", "-y",
    "-i", video_path,
    "-c:v", "libx264",
    "-preset", "fast",
    "-pix_fmt", "yuv420p",
    FINAL_MP4_PATH
]
print(f"Converting video to MP4 at: {FINAL_MP4_PATH}")
subprocess.run(cmd, check=True)

print(f"Demo video successfully created at: {FINAL_MP4_PATH}")
