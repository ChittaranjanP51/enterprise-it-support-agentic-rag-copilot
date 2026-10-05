"""Record a narrated demo video of the running app (for LinkedIn).

Requires the app running on http://localhost:8000 and:
    pip install playwright imageio-ffmpeg && python -m playwright install chromium
Usage:  python scripts/make_demo_video.py
Output: video/demo_narrated.mp4 (Windows TTS voice) and video/demo_silent.mp4 (dub your own voice)
"""
import base64
import subprocess
import time
import wave
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "video"
AUDIO = OUT / "narration"
URL = "http://localhost:8000"
VOICE = "Microsoft Zira Desktop"
W, H = 1280, 720

NARRATION = {
    "intro": "IT teams answer the same questions every day: VPN resets, leave policy, Wi-Fi. "
             "I built an AI copilot that handles them, and it decides how to answer each question.",
    "flow": "It's an agentic RAG system built with LangGraph. A router decides what to do. It searches "
            "our private knowledge base in Pinecone, grades the evidence, and only goes to the web "
            "through Tavily if the internal documents aren't enough.",
    "app": "Here it is, running locally on FastAPI.",
    "leave": "First, an HR question. It finds the policy in our knowledge base and answers: 22 days, "
             "with 5 carried over. The source badge says knowledge base, and the confidence is good.",
    "vpn": "Now an IT question. Step by step instructions, taken straight from the company policy.",
    "python": "This one isn't in our documents, so it automatically searches the web and answers from "
              "there. The source badge now says web, with the links it used.",
    "hi": "And small talk gets a quick direct reply, with no unnecessary searching.",
    "fallback": "If neither the knowledge base nor the web is good enough, it still answers, but clearly "
                "says it's unverified. No confident guessing.",
    "outro": "It's containerised with Docker and ready to deploy on DigitalOcean. Code is linked below.",
}

QUESTIONS = [
    ("leave", "How many days of annual leave do we get?"),
    ("vpn", "How do I reset my VPN password?"),
    ("python", "What's the latest stable Python version?"),
    ("hi", "Hi, thanks!"),
]

CARD_CSS = """
<style>
 body{margin:0;width:%dpx;height:%dpx;display:flex;flex-direction:column;align-items:center;
      justify-content:center;background:#0f1320;color:#e8ebf5;font-family:system-ui,sans-serif}
 h1{font-size:40px;margin:0 0 8px} p{color:#9aa3b8;font-size:20px;margin:0 0 22px}
 img{max-width:1100px;max-height:520px;border-radius:12px;box-shadow:0 10px 40px #0008}
 ul{font-size:24px;line-height:1.8;color:#cfd5e6} .tag{display:inline-block;margin:6px;padding:8px 16px;
 border-radius:99px;background:#4f46e5;color:#fff;font-size:20px}
</style>""" % (W, H)


def tts(key: str, text: str) -> float:
    """Synthesize text to WAV with Windows SAPI; return its duration in seconds."""
    path = AUDIO / f"{key}.wav"
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.SelectVoice('{VOICE}');$s.Rate=0;"
        f"$s.SetOutputToWaveFile('{path}');$s.Speak($env:TTS_TEXT);$s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True,
                   env={**__import__("os").environ, "TTS_TEXT": text})
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def main():
    AUDIO.mkdir(parents=True, exist_ok=True)
    durations = {k: tts(k, t) for k, t in NARRATION.items()}
    print("narration:", {k: round(v, 1) for k, v in durations.items()})

    img = base64.b64encode((ROOT / "docs/assets/architecture.png").read_bytes()).decode()
    intro_html = (f"{CARD_CSS}<h1>Enterprise IT Support Agentic RAG Copilot</h1>"
                  f"<p>Knowledge base first, web if needed, honest fallback</p>"
                  f"<img src='data:image/png;base64,{img}'>")
    outro_html = (f"{CARD_CSS}<h1>Honest by design</h1><ul>"
                  "<li>Every answer shows its source, confidence and citations</li>"
                  "<li>Weak evidence &rarr; web search &rarr; clearly labelled fallback</li>"
                  "<li>Docker image, deployable on DigitalOcean</li></ul><div>"
                  + "".join(f"<span class='tag'>{t}</span>" for t in
                            ["LangGraph", "FastAPI", "Pinecone", "OpenAI / Groq", "Tavily", "Docker"])
                  + "</div>")

    cues: list[tuple[str, float]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H},
                                  record_video_dir=str(OUT / "raw"), record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        t0 = time.time()

        def say(key: str, pad: float = 0.6):
            cues.append((key, time.time() - t0))
            time.sleep(durations[key] + pad)

        page.set_content(intro_html)
        time.sleep(0.8)
        say("intro")
        say("flow", 1.0)

        page.goto(URL)
        page.wait_for_selector("#q")
        say("app", 0.4)

        for key, question in QUESTIONS:
            n = page.locator(".meta").count()
            page.click("#q")
            page.type("#q", question, delay=55)
            time.sleep(0.3)
            page.keyboard.press("Enter")
            page.wait_for_function(
                f"document.querySelectorAll('.meta').length > {n} || "
                "[...document.querySelectorAll('.msg')].some(m => m.textContent.startsWith('Error:'))",
                timeout=120_000)
            if page.locator(".meta").count() == n:
                raise RuntimeError(f"App returned an error for {question!r}; re-run the script")
            say(key, 1.2)

        page.set_content(outro_html)
        time.sleep(0.5)
        say("fallback", 0.4)
        say("outro", 1.5)

        video_path = Path(page.video.path())
        ctx.close()
        browser.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    silent = OUT / "demo_silent.mp4"
    narrated = OUT / "demo_narrated.mp4"
    venc = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20", "-r", "30"]
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(video_path), *venc, "-an", str(silent)], check=True)

    inputs, filters = ["-i", str(silent)], []
    for i, (key, start) in enumerate(cues, start=1):
        inputs += ["-i", str(AUDIO / f"{key}.wav")]
        ms = int(start * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(1, len(cues) + 1))
    filters.append(f"{mix}amix=inputs={len(cues)}:normalize=0[aout]")
    subprocess.run([ff, "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", str(narrated)], check=True)

    (OUT / "cue_sheet.txt").write_text(
        "\n".join(f"{int(s // 60)}:{s % 60:04.1f}  {k}: {NARRATION[k]}" for k, s in cues), encoding="utf-8")
    print("wrote", narrated, "and", silent)


if __name__ == "__main__":
    main()
