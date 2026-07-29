import os
import sys
import json
import time
import queue
import io
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
import pygame
from groq import Groq
import edge_tts
import vosk

# =====================================================================
# API KEYS & CONFIGURATION
# =====================================================================
API_KEYS = {
    "GROQ": "YOUR_GROQ_API_KEY",
    "OPENROUTER": "YOUR_OPENROUTER_API_KEY",
    "MODELSCOPE": "YOUR_MODELSCOPE_API_KEY",
    "NVIDIA": "YOUR_NVIDIA_API_KEY",
    "GEMINI": "YOUR_GEMINI_API_KEY"
}

DEFAULT_PROVIDER = "GROQ"
TTS_VOICE = "en-US-AvaNeural"
SAMPLE_RATE = 16000

# Initialize Pygame Audio Engine (44.1kHz, 16-bit Mono)
pygame.mixer.init(frequency=44100, size=-16, channels=1)

# Initialize Groq Client
groq_client = Groq(api_key=API_KEYS["GROQ"])
audio_queue = queue.Queue()

# =====================================================================
# 1. UNIFIED PYGAME CHIME (Zero Audio Driver Collisions)
# =====================================================================
def play_chime():
    """Generates and plays a clean dual-tone ping chime via Pygame."""
    print("\n● [PING!] Wake word recognized!")
    sr = 44100
    duration = 0.25
    t = np.linspace(0, duration, int(sr * duration), False)
    
    # Acoustic chord: 880Hz (A5) + 1108Hz (C#6) with smooth exponential decay
    tone = 0.3 * np.sin(2 * np.pi * 880 * t) + 0.3 * np.sin(2 * np.pi * 1108 * t)
    envelope = np.exp(-7 * t)
    audio = (tone * envelope * 32767).astype(np.int16)

    # Stream directly through Pygame
    sound = pygame.mixer.Sound(buffer=audio.tobytes())
    sound.play()
    time.sleep(duration + 0.05) # Wait for chime to complete

# =====================================================================
# 2. NEURAL TEXT-TO-SPEECH (edge-tts)
# =====================================================================
async def _generate_tts_async(text, output_file="response.mp3"):
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(output_file)

def speak_text(text):
    """Converts text to speech and plays via Pygame."""
    print(f"● Kestrel: \"{text}\"\n")
    output_file = "response.mp3"
    
    asyncio.run(_generate_tts_async(text, output_file))
    
    pygame.mixer.music.load(output_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
        
    pygame.mixer.music.unload()
    if os.path.exists(output_file):
        os.remove(output_file)

# =====================================================================
# 3. QUESTION RECORDING & STT
# =====================================================================
def record_question(duration=4.5):
    """Captures user's spoken question right after the chime."""
    print("● [RECORDING] Speak your question now...")
    recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()
    
    wav_io = io.BytesIO()
    sf.write(wav_io, recording, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    wav_io.seek(0)
    wav_io.name = "question.wav"
    return wav_io

def transcribe_audio(wav_io):
    """Groq Whisper STT (~100ms response time)."""
    print("● Transcribing speech...")
    try:
        transcription = groq_client.audio.transcriptions.create(
            file=wav_io,
            model="whisper-large-v3-turbo",
            response_format="json",
            language="en"
        )
        text = transcription.text.strip()
        print(f"● You: \"{text}\"")
        return text
    except Exception as e:
        print(f"STT Error: {e}")
        return None

# =====================================================================
# 4. LLM REASONING (Groq Default + Fallbacks)
# =====================================================================
def query_llm(user_prompt, provider=DEFAULT_PROVIDER):
    """Requests short, conversational answer from LLM."""
    print(f"● Processing via [{provider}]...")
    
    system_prompt = (
        "You are Kestrel, an intelligent voice assistant. Answer in 1 to 2 short sentences. "
        "Be direct, clear, and natural for speech output."
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,
            max_tokens=100
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return "I had trouble retrieving an answer."

# =====================================================================
# 5. MAIN LOOP
# =====================================================================
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

def main():
    print("● Loading Vosk wake word engine...")
    model = vosk.Model(lang="en-us")
    
    grammar = '["hey kestrel", "hello kestrel", "[unk]"]'
    recognizer = vosk.KaldiRecognizer(model, 16000, grammar)
    recognizer.SetWords(True)

    print("\n--------------------------------------------------")
    print("● KESTREL ASSISTANT READY")
    print("  Say 'Hey Kestrel' into your microphone.")
    print("--------------------------------------------------\n")

    with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16',
                           channels=1, callback=audio_callback):
        while True:
            data = audio_queue.get()
            
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "")
                
                if "hey kestrel" in text or "hello kestrel" in text:
                    # 1. Play Chime
                    play_chime()
                    
                    # 2. Record Question
                    wav_io = record_question(duration=4.0)
                    
                    # 3. Transcribe with Groq Whisper
                    user_text = transcribe_audio(wav_io)
                    
                    if user_text and len(user_text) > 2:
                        # 4. Query Groq LLM
                        response_text = query_llm(user_text, provider="GROQ")
                        
                        # 5. Speak Response
                        speak_text(response_text)
                    else:
                        print("● No speech detected.")
                    
                    # Flush old queue data
                    while not audio_queue.empty():
                        audio_queue.get()
                        
                    print("● Listening for 'Hey Kestrel'...\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Kestrel Assistant. ●")
