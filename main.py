import os
from typing import List, Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
from pydantic import BaseModel
import json

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app = FastAPI(title="Music Practice Exercise Generator")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration for open-webui API
WEBUI_ENABLED = True  # Set to use open-webui API
WEBUI_BASE_URL = "https://chat.ivislabs.in/api"
API_KEY = "sk-2e7ff0df727b4f08a97b86e1e78df6b9"  # Replace with your actual API key if needed
DEFAULT_MODEL = "gemma2:2b"  # Update to one of the available models

# Fallback to local Ollama API if needed
OLLAMA_ENABLED = True  # Set to False to use only the web UI API
OLLAMA_HOST = "localhost"
OLLAMA_PORT = "11434"
OLLAMA_API_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api"

# Define the prompt template for music practice exercises
MUSIC_EXERCISE_PROMPT = """
You are a music teacher helping students improve their skills. Generate {num_exercises} practice exercises for a student with a skill level of {skill_level}. 
The exercises should focus on {focus_area} and be appropriate for their level. Include detailed instructions for each exercise.

Skill Level: {skill_level}
Focus Area: {focus_area}
Number of Exercises: {num_exercises}
"""

class GenerationRequest(BaseModel):
    skill_level: str
    num_exercises: int = 3
    focus_area: str = "scales and technique"
    tone: Optional[str] = "encouraging"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate_exercises(
    skill_level: str = Form(...),
    num_exercises: int = Form(3),
    focus_area: str = Form("scales and technique"),
    tone: str = Form("encouraging"),
    model: str = Form(DEFAULT_MODEL)
):
    try:
        # Build the prompt using the template
        prompt = MUSIC_EXERCISE_PROMPT.format(
            skill_level=skill_level,
            num_exercises=num_exercises,
            focus_area=focus_area,
            tone=tone
        )

        # Try using the open-webui API first if enabled
        if WEBUI_ENABLED:
            try:
                # Prepare message for API format
                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                # Call Chat Completions API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{WEBUI_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": messages
                        },
                        timeout=10.0  # Reduce timeout for faster failure
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Extract generated text from the response
                        generated_text = ""
                        if "choices" in result and len(result["choices"]) > 0:
                            choice = result["choices"][0]
                            if "message" in choice and "content" in choice["message"]:
                                generated_text = choice["message"]["content"]
                            elif "text" in choice:
                                generated_text = choice["text"]
                        elif "response" in result:
                            generated_text = result["response"]

                        if generated_text:
                            return JSONResponse(content={"generated_exercises": generated_text})
            except Exception as e:
                print(f"Open-webui API attempt failed: {str(e)}")

        # Fallback to direct Ollama API if enabled and web UI failed
        if OLLAMA_ENABLED:
            try:
                print("Falling back to direct Ollama API")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{OLLAMA_API_URL}/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=10.0  # Reduce timeout for faster failure
                    )

                    if response.status_code == 200:
                        result = response.json()
                        generated_text = result.get("response", "")
                        return JSONResponse(content={"generated_exercises": generated_text})
                    else:
                        raise HTTPException(status_code=500, detail="Failed to generate content from Ollama API")
            except Exception as e:
                print(f"Ollama API attempt failed: {str(e)}")

        # If we get here, both attempts failed
        hardcoded_response = """
        Beginner Scale Practice Exercise

        This exercise will help you develop a strong foundation in playing scales with good posture and hand control.

        Warm-up: (2 minutes)
        Before starting, play simple chords or arpeggios to warm up your hands and body.

        Exercise:
        1. Find your comfortable position: Sit comfortably at your instrument with a straight posture.
        2. Choose a C major scale: Begin by playing the notes of the C Major scale: C-D-E-F-G-A-B-C.
        3. Practice slowly and clearly: Focus on producing clear, articulate notes without rushing.
        4. Pay attention to hand position: Keep your wrist straight and fingers relaxed.
        5. Practice in two patterns: Start on the first note (C) and play up and down the scale.

        Tips for Beginners:
        - Use a metronome: Start with slow tempos (e.g., 60 beats per minute).
        - Record yourself playing: Identify areas for improvement.

        Remember: Practice makes progress!
        """
        return JSONResponse(content={"generated_exercises": hardcoded_response})

    except Exception as e:
        import traceback
        print(f"Error generating music exercises: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating music exercises: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)