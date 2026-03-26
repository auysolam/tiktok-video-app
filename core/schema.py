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
