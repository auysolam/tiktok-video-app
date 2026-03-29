from pydantic import BaseModel, Field
from typing import List, Literal

class VideoScene(BaseModel):
    scene_number: int = Field(description="ลำดับของซีน เริ่มจาก 1")
    timecode_start: str = Field(description="เวลาเริ่มต้นของซีน (เช่น '00:00')")
    timecode_end: str = Field(description="เวลาสิ้นสุดของซีน (เช่น '00:08')")
    script: str = Field(description="บทพูดสำหรับเสียงพากย์ในซีนนี้")
    image_prompt: str = Field(description="Prompt ภาษาอังกฤษสำหรับไปเจนภาพขนาด 9:16 ให้สอดคล้องกับบทพูดและสินค้า")
    video_prompt: str = Field(description="Prompt ภาษาอังกฤษสำหรับนำภาพไปทำเป็นวิดีโอเคลื่อนไหว (เช่น 'Subtle camera pan, natural movement')")

class VideoPlan(BaseModel):
    product_name: str = Field(description="ชื่อสินค้าที่วิเคราะห์จากภาพ")
    target_audience: str = Field(description="กลุ่มเป้าหมายของสินค้านี้")
    character_type: Literal["male", "female", "custom"] = Field(description="ประเภทของตัวละครที่ใช้พากย์และแสดงนำ")
    music_mood: Literal["upbeat", "chill", "suspense", "none"] = Field(description="อารมณ์ของเพลงประกอบ")
    scenes: List[VideoScene] = Field(description="รายการซีนทั้งหมด โดยแต่ละซีนมีความยาวประมาณ 8 วินาที")

class TikTokPostData(BaseModel):
    product_details: str = Field(description="1. รายละเอียดสินค้าที่วิเคราะห์จากภาพ (ชื่อ, จุดเด่น, สรรพคุณ)")
    overlay_text: str = Field(description="2. ข้อความสั้นๆ ดึงดูดความสนใจสำหรับแปะบนวิดีโอ (เช่น โปรโมชั่น, ราคา, ส่งฟรี)")
    post_caption: str = Field(description="3. ข้อความโพสต์ขายสินค้า (Caption) เขียนให้น่าสนใจและกระตุ้นการซื้อ")
    hashtags: str = Field(description="4. แฮชแท็กที่เกี่ยวข้องกับสินค้า (เช่น #เสื้อผ้าแฟชั่น #ของดีบอกต่อ)")
    link_title: str = Field(description="5. ชื่อสินค้า+ราคา หรือข้อความสั้นๆ ไม่เกิน 30 ตัวอักษร สำหรับใส่หัวข้อลิงก์ตะกร้า (เช่น 'กดสั่งซื้อ 59 บาท' หรือ 'เดรสลดราคาพิเศษ')")
