import edge_tts
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import uuid
import os
import subprocess
import re

app = FastAPI(title="Edge TTS Belgesel API", version="1.0")

class TTSRequest(BaseModel):
    text: str
    filename: str = "ses.mp3"

def classify_sentence(sentence):
    """Cümle tipini belirle ve ayarları döndür"""
    sentence = sentence.strip()
    
    if '!' in sentence:
        return {"rate": "-3%", "pitch": "+1Hz", "volume": "+5%"}
    elif '?' in sentence:
        return {"rate": "-5%", "pitch": "+2Hz", "volume": "+2%"}
    else:
        return {"rate": "-8%", "pitch": "-2Hz", "volume": "+0%"}

def smart_split_by_emotion(text):
    """Cümleleri duygularına göre böl"""
    text = text.replace("\n", " ").strip()
    text = re.sub(r'\s+', ' ', text)
    
    sentences = re.split(r'([.!?]+\s*)', text)
    
    result = []
    for i in range(0, len(sentences)-1, 2):
        if sentences[i].strip():
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
            result.append(sentence.strip())
    
    return result if result else [text]

@app.post("/generate")
async def generate_audio(req: TTSRequest):
    request_id = str(uuid.uuid4())[:8]
    temp_files = []
    file_list = f"files_{request_id}.txt"
    output_file = f"output_{request_id}.mp3"
    
    try:
        sentences = smart_split_by_emotion(req.text)
        
        print(f"📝 {len(sentences)} cümle işleniyor...")
        
        # Her cümleyi ayrı üret
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            temp_file = f"sent_{request_id}_{i}.mp3"
            settings = classify_sentence(sentence)
            
            emoji = "❗" if '!' in sentence else "❓" if '?' in sentence else "📖"
            print(f"   {emoji} {i+1}/{len(sentences)}")
            
            communicate = edge_tts.Communicate(
                text=sentence,
                voice="tr-TR-AhmetNeural",
                rate=settings['rate'],
                pitch=settings['pitch'],
                volume=settings['volume']
            )
            
            await communicate.save(temp_file)
            temp_files.append(temp_file)
        
        # Dosya listesi oluştur
        with open(file_list, "w", encoding="utf-8") as f:
            for tf in temp_files:
                f.write(f"file '{tf}'\n")
        
        # FFmpeg ile birleştir
        cmd = (
            f'ffmpeg -y -f concat -safe 0 -i {file_list} '
            f'-af "silenceremove='
            f'start_periods=1:start_threshold=-50dB:start_duration=0.05:'
            f'stop_periods=-1:stop_threshold=-50dB:stop_duration=0.4,'
            f'apad=pad_dur=0.6" '
            f'-c:a libmp3lame -b:a 320k {output_file}'
        )
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Fallback: basit birleştirme
            cmd = f'ffmpeg -y -f concat -safe 0 -i {file_list} -c:a libmp3lame -b:a 320k {output_file}'
            subprocess.run(cmd, shell=True, capture_output=True)
        
        # Dosyayı oku
        with open(output_file, 'rb') as f:
            audio_data = f.read()
        
        print("✅ Tamamlandı")
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={'Content-Disposition': f'attachment; filename="{req.filename}"'}
        )
        
    except Exception as e:
        print(f"❌ {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Temizlik
        for tf in temp_files:
            try:
                if os.path.exists(tf):
                    os.remove(tf)
            except:
                pass
        
        try:
            if os.path.exists(file_list):
                os.remove(file_list)
            if os.path.exists(output_file):
                os.remove(output_file)
        except:
            pass

@app.get("/")
def root():
    return {
        "status": "ready",
        "model": "Edge TTS - Ahmet (Erkek Ses)",
        "version": "1.0",
        "features": [
            "✅ Türkçe belgesel anlatımı",
            "✅ Duygulu okuma (!, ?)",
            "✅ Cümleler arası doğal ara (0.4s)",
            "✅ Sonda yumuşak bitiş (0.6s)",
            "✅ 320kbps kalite"
        ],
        "usage": {
            "endpoint": "/generate",
            "method": "POST",
            "body": {
                "text": "Belgesel metniniz",
                "filename": "ses.mp3"
            }
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
