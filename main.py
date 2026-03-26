import os
from core.gemini_engine import generate_video_plan
from core.video_editor import assemble_tiktok_video
from core.asset_generator import process_all_assets
from core.schema import VideoPlan
import json
import asyncio

def run_pipeline(image_path: str):
    print("🎬 เริ่มกระบวนการสร้างวิดีโอ TikTok อัตโนมัติ (End-to-End)\n")
    
    # --- PHASE 1: การคิดสคริปต์ (Data & Scripting) ---
    print("==== [1] กระบวนการวิเคราะห์ภาพ (Gemini Engine) ====")
    try:
        json_result = generate_video_plan(image_path)
        # นำ JSON string ที่ได้จาก Gemini ไปแปลงเป็น Pydantic Object
        video_plan = VideoPlan.model_validate_json(json_result)
        print(f"✅ สร้างแผนการสำเร็จ! สินค้า: {video_plan.product_name}")
        
    except Exception as e:
        print(f"❌ ล้มเหลวในขั้นตอนการคิดสคริปต์: {e}")
        return

    # --- PHASE 2: การสร้างวัตถุดิบ (Asset Generation - T2S, T2I, I2V) ---
    print("\n==== [2] กระบวนการสร้างวัตถุดิบ (Asset Generation) ====")
    # เรียกใช้ edge-tts และ Mockup API สร้างภาพ/วิดีโอ
    asyncio.run(process_all_assets(video_plan))
    print("✅ เตรียมไฟล์วัตถุดิบทั้งหมดเสร็จสิ้น!\n")
    
    # --- PHASE 3: ตัดต่อประกอบร่าง (Automated Editing) ---
    print("==== [3] กระบวนการตัดต่ออัตโนมัติ (MoviePy) ====")
    # ตรวจสอบว่าโฟลเดอร์ output มีหรือยัง
    os.makedirs("../output", exist_ok=True)
    output_path = f"../output/{video_plan.product_name.replace(' ', '_')}_tiktok.mp4"
    
    # ส่งแผนงานทั้งหมดไปให้ระบบตัดต่อจัดการโหลดไฟล์จากโฟลเดอร์ assets มาประกอบกัน
    assemble_tiktok_video(video_plan, output_path)

if __name__ == "__main__":
    test_image_path = "../assets/input/sample_product.jpg"
    
    if os.path.exists(test_image_path):
        run_pipeline(test_image_path)
    else:
        print(f"⚠️ กรุณานำภาพสินค้าไปวางไว้ที่: {test_image_path}")
        print("และโปรดตรวจสอบว่าได้ตั้งค่าไลบรารีและไฟล์ .env สำหรับ API Key เรียบร้อยแล้ว")
