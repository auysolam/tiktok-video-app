import os
import asyncio
# ใช้ edge-tts ในการสร้างเสียงพากย์ภาษาไทยได้ฟรีและเสียงเป็นธรรมชาติพอสมควร
# (ต้องติดตั้ง: pip install edge-tts)
import edge_tts

# นำเข้าโครงสร้างข้อมูลที่เราเขียนไว้
from core.schema import VideoPlan

async def generate_voiceover(text: str, output_path: str, voice: str = "th-TH-PremwadeeNeural"):
    """
    สร้างเสียงพากย์ด้วย Edge TTS (ใช้ฟรี ไม่ต้องมี API Key)
    """
    print(f"🎙️ กำลังสร้างเสียงพากย์: '{text[:20]}...'")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_image(prompt: str, output_path: str):
    """
    [MOCKUP] ฟังก์ชันส่ง Prompt ไปให้ Image Generation API (เช่น Midjourney, Stable Diffusion)
    """
    print(f"🖼️ [MOCKUP] กำลังเจนภาพ 9:16 ด้วย Prompt: '{prompt[:20]}...'")
    # ตรงนี้คุณจะต้องเขียนโค้ดเรียกใช้งาน API เจ้าที่คุณเลือก (เช่น requests.post(...) ไปยัง API ภายนอก)
    # สมมติว่าได้ไฟล์กลับมาแล้ว เราจะใช้ภาพที่มีอยู่จำลองการทำงานแทน
    
    # --- จำลองการได้ไฟล์ภาพมา ---
    if not os.path.exists(output_path):
        import shutil
        import glob
        import re
        
        # ดึงภาพที่ผู้ใช้อัปโหลดมาใช้งานเป็น Mockup (สลับภาพตามเลขซีน)
        uploaded_imgs = sorted(glob.glob("../assets/input/app_uploaded_product_*.jpg"))
        if uploaded_imgs:
            m = re.search(r'scene_(\d+)', output_path)
            idx = (int(m.group(1)) - 1) if m else 0
            # เลือกสลับภาพไปเรื่อยๆ ตามจำนวนที่มี
            sample_img = uploaded_imgs[idx % len(uploaded_imgs)]
            shutil.copy(sample_img, output_path)

def generate_video(image_path: str, video_prompt: str, output_path: str):
    """
    [MOCKUP] ฟังก์ชันส่งภาพและ Prompt ไปให้ Video Generation API (เช่น Runway Gen-3, Luma)
    """
    print(f"🎞️ [MOCKUP] กำลังแปลภาพนิ่งเป็นวิดีโอด้วย Prompt: '{video_prompt[:20]}...'")
    # ตรงนี้ต้องเชื่อม API ทำวิดีโอ ซึ่งส่วนใหญ่จะใช้เวลา Process นาน
    # (อาจต้องเขียน loop เช็คสถานะ API ทุกๆ 10 วินาที)
    
    # --- จำลองการได้ไฟล์วิดีโอมา ---
    # ในการติดตั้งจริง หากไม่เชื่อมต่อ API ตัว MoviePy (Phase 3) 
    # จะแจ้งเตือน ข้ามซีนนี้ และอาจจะใช้ภาพนิ่งแทน ถ้าคุณอยากลองทดสอบคุณสามารถ
    # เอาไฟล์ .mp4 ดัมมี่ไปวางทับในชื่อที่ตรงกันได้
    pass

async def process_all_assets(plan: VideoPlan):
    """
    ลูปทำงานสร้าง Asset สำหรับทุกๆ ซีน
    """
    os.makedirs("../assets/audio", exist_ok=True)
    os.makedirs("../assets/video", exist_ok=True)
    os.makedirs("../assets/images", exist_ok=True)
    
    # จัดการเรืองเสียง (เลือกตัวละคร)
    voice_profile = "th-TH-PremwadeeNeural" if plan.character_type == "female" else "th-TH-NiwatNeural"
    
    for scene in plan.scenes:
        print(f"\n--- เริ่มรวบรวมวัตถุดิบ ซีนที่ {scene.scene_number} ---")
        
        audio_path = f"../assets/audio/scene_{scene.scene_number}.mp3"
        img_path = f"../assets/images/scene_{scene.scene_number}.jpg"
        video_path = f"../assets/video/scene_{scene.scene_number}.mp4"
        
        # 1. สร้างเสียงพากย์ (ทำงานจริง)
        if not os.path.exists(audio_path):
            await generate_voiceover(scene.script, audio_path, voice=voice_profile)
        else:
            print("🎙️ (ข้าม) มีไฟล์เสียงพากย์อยู่แล้ว")
            
        # 2. สร้างภาพนิ่ง
        if not os.path.exists(img_path):
            generate_image(scene.image_prompt, img_path)
            
        # 3. สร้างวิดีโอเคลื่อนไหว
        if not os.path.exists(video_path):
            generate_video(img_path, scene.video_prompt, video_path)

if __name__ == "__main__":
    print("ไฟล์อรรถประโยชน์สำหรับการเจน เสียง ภาพ และวิดีโอ")
