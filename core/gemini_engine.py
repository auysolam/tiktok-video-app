import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# นำเข้าโครงสร้างข้อมูลที่เราเขียนไว้
from core.schema import VideoPlan

# โหลด API Key จากไฟล์ .env (คุณต้องสร้างไฟล์ .env และใส่ GEMINI_API_KEY=xxx)
load_dotenv()

from typing import List
import os
import time
import streamlit as st

def _safe_generate_content(client, model, contents, config, max_retries=3, fallback_prompt=None):
    """
    ฟังก์ชันช่วยรัน API และรออัตโนมัติหากเจอ (429 RESOURCE_EXHAUSTED)
    """
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    try:
                        st.warning(f"⚠️ ระบบติดเครื่องหมาย Rate Limit (โควต้าเต็มชั่วคราว) โปรดรอสัก 30 วินาทีแล้วกดปุ่มใหม่อีกครั้งนะครับ")
                        
                        # สร้างระบบก๊อปสำรองรวมถึง System Instruction (ถ้ามี)
                        backup_text = ""
                        
                        if fallback_prompt:
                            backup_text = fallback_prompt
                        else:
                            sys_instruct = getattr(config, "system_instruction", None)
                            if sys_instruct:
                                backup_text += f"[คำสั่งหลักสำหรับ AI (System Instruction)]:\n{sys_instruct}\n\n"
                                backup_text += f"[ข้อมูลที่ต้องนำไปวิเคราะห์]:\n"
                                
                            if isinstance(contents, list):
                                for item in contents:
                                    if isinstance(item, str):
                                        backup_text += item + "\n"
                            elif isinstance(contents, str):
                                backup_text += contents
                            
                        if backup_text.strip():
                            st.info("💡 **ระบบก๊อปสำรอง (Backup Prompt):** ระหว่างรอ... คุณสามารถก๊อปปี้คำสั่งนี้ไปให้ Gemini ในเว็บร่างบทแทนได้เลยครับ ถ้ารีบ!")
                            st.code(backup_text.strip(), language="text")
                    except Exception as try_e:
                        pass
                    # หยุดการทำงานทันทีเพื่อให้ UI แสดงผลรหัสสำรอง ไม่ต้อง sleep แช่แข็งจอผู้ใช้
                    raise Exception("429 Rate Limit - แสดงรหัสสำรองให้ผู้ใช้แล้ว")
                else:
                    raise e
            else:
                raise e


def generate_image_from_prompt(prompt: str, output_path: str):
    """
    ใช้ AI เจนภาพนิ่งโดยตรงจาก Gemini API Key (รุ่น Imagen 3) ตามที่ผู้ใช้รีเควส
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    
    try:
        # ใช้ Imagen 3 Model ของ Google ด้วยคลาสใหม่ล่าสุด
        result = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
            )
        )
        
        for generated_image in result.generated_images:
            # Save the image
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            image.save(output_path)
            return True, ""
            
    except Exception as e:
        print(f"Imagen Generation Error: {e}")
        error_msg = str(e)
        if "404" in error_msg and ("imagen" in error_msg.lower() or "not found" in error_msg.lower()):
            error_msg = "Google API Key ของคุณยังไม่ได้รับสิทธิ์ใช้งานระบบวาดภาพ Imagen 3 (ฟีเจอร์นี้อาจต้องเปิดใช้งานระดับสูงหรือเสียเงินใน Google Cloud) คำแนะนำ: กรุณาใช้ปุ่ม 'ก๊อปปี้ไปเจนบนเว็บ' ในโหมดแมนนวลแทนครับ"
        elif "429" in error_msg or "RESOURCE" in error_msg:
            error_msg = "โควต้า AI เต็มชั่วคราว โปรดรอสักครู่แล้วลองใหม่นะฮะ"
            
        # ถ้าเจอปัญหา จะวาด Mockup พร้อมคำแนะนำภาษาไทยอธิบาย Error ให้ผู้ใช้รู้ตัวแบบสวยๆ
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (1080, 1920), color = (73, 109, 137))
        d = ImageDraw.Draw(img)
        # เนื่องจากไม่มีฟอนต์ไทย อาจจะอ่านยากถ้าเรนเดอร์ลงรูป งั้นใส่แค่คำสั้นๆ ลงรูป
        d.text((50, 500), f"API Error / Cannot Generate Image\n\nTips: Please use Manual Mode\ninstead of Auto Mode.", fill=(255,255,255))
        img.save(output_path)
        return False, error_msg

def analyze_product_from_images(image_paths: List[str], ai_model: str = 'gemini-2.5-flash') -> str:
    """
    วิเคราะห์ภาพสินค้าและดึงจุดขาย (Sales Pitch / Product Details) ออกมาเป็นข้อความ
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    
    import PIL.Image
    uploaded_images = []
    for path in image_paths:
        try:
            img = PIL.Image.open(path)
            uploaded_images.append(img)
        except:
            pass
            
    # ใช้ Schema ใหม่สำหรับโพสต์
    from core.schema import TikTokPostData
    
    system_instruction = f"""คุณคือนักการตลาดมือทองบน TikTok ช่วยดูภาพสินค้าต่อไปนี้แล้วเขียนข้อมูลสำหรับโพสต์ขายของ:
1. รายละเอียดสินค้า (วิเคราะห์จากภาพ)
2. ข้อความสั้นๆ ดึงดูดใจไว้แปะบนวิดีโอ (เน้นสั้นๆ เช่น โปรโมชั่น ราคา ส่งฟรี)
3. ข้อความโพสต์ขาย (Caption)
4. แฮชแท็กสินค้า
5. ชื่อสินค้า+ราคา หรือข้อความปุ่มตะกร้า (ไม่เกิน 30 ตัวอักษร เช่น 'กดสั่งซื้อ 59 บาท')

ส่งข้อมูลกลับมาในรูปแบบ JSON ตาม Schema นี้เท่านั้น:
{TikTokPostData.model_json_schema()}"""
    
    user_backup_prompt = """ช่วยวิเคราะห์ข้อมูลสินค้าจากภาพและร่างรายละเอียดสำหรับการโพสต์ขาย TikTok ให้หน่อย
1.คำเขียนหน้าปกคลิป
2.คำอธิบายสินค้า ไม่ต้องยาวมาก เน้นดึงดูด โปรโมชั่น ราคา 
3.#แฮชแท็ก 
4.ชื่อสินค้า ราคา ความยาวไม่เกิน 30 คำ
5.ข้อความแปะคลิป เช่น ราคา โปรโมชั่น เน้นให้ว้าว หยุดดูเลย แต่ข้อความสั้นๆ ไม่ต้องยาว"""

    response = _safe_generate_content(
        client=client,
        model=ai_model,
        contents=uploaded_images + ["ช่วยวิเคราะห์ข้อมูลสินค้าจากภาพและร่างรายละเอียดสำหรับการโพสต์ขาย TikTok ให้หน่อย ตอบกลับเป็น JSON เท่านั้น"],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.7,
        ),
        fallback_prompt=user_backup_prompt
    )
    return response.text

def generate_video_plan(image_paths: List[str], product_details: str, character_type: str, character_skin: str, character_traits: str, use_sfx: bool, num_scenes: int, scene_duration: int, product_scene_count: int, background: str, voice_type: str, voice_emotion: str, no_voiceover: bool = False, fashion_mode: bool = False, fashion_item_type: str = "", ai_model: str = 'gemini-2.5-flash') -> VideoPlan:
    """
    รับรายการภาพสินค้าและใช้ Gemini สร้างแผนการทำวิดีโอ (JSON) กลับมา โดยอิงตามการตั้งค่าตัวละครและโครงสร้าง
    """
    # ตรวจสอบ API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY in .env file")

    # ตั้งค่า API Key
    client = genai.Client(api_key=api_key)
    
    # อัปโหลดภาพไปยัง API
    import PIL.Image
    uploaded_images = []
    print(f"กำลังอัปโหลดภาพจำนวน {len(image_paths)} ภาพ...")
    for path in image_paths:
        try:
            img = PIL.Image.open(path)
            uploaded_images.append(img)
        except Exception as e:
            print(f"ข้ามภาพ {path} เนื่องจาก: {e}")
    
    # กำหนดเนื้อหา Sound Effect
    sfx_prompt = "ให้ใส่เสียง Sound Effects หรือ BGM กวนๆ ตลกๆ หรือตื่นเต้น แทรกในวงเล็บของ script ด้วย เช่น [เสียงตู้ม] หรือ [เสียงหัวเราะ]" if use_sfx else "ห้ามใส่ Sound Effects ลงในบทพูด ให้ใช้เสียงพากย์ล้วนๆ"

    script_instruction = '3. คิดบทพากย์ (script) ที่ดึงดูด น่าสนใจ เป็นเรื่องราวเนื้อหาต่อเนื่องกันแบบเนียนๆ ตั้งแต่ซีนแรกจนถึงซีนสุดท้าย (ห้ามตัดจบดื้อๆ) และสอดคล้องกับ "เสียงผู้พากย์" และ "อารมณ์น้ำเสียง" ที่กำหนดไว้ข้างต้นอย่างเคร่งครัด ใช้ภาษาไทยสไตล์วัยรุ่น TikTok'
    video_voice_instruction = f'- **สำคัญด้านเสียงและภาพต่อเนื่อง:** ต้องบังคับใน Prompt ให้เครื่องมือสร้างวิดีโอจ่ายทั้งภาพและเสียงที่ต่อเนื่องกัน โดยสั่งว่า "Continuous seamless extension from previous scene, EXACTLY the same character, same environment. Include perfectly synchronized voiceover narration in {voice_type} voice with {voice_emotion} tone, EXACTLY the same voice identity as previous clips"'

    # คำสั่ง (Prompt) ที่บังคับให้ AI ทำตาม    
    if "ไม่มีตัวละคร" in character_type:
        char_rule = f"- เป็นวิดีโอโชว์สินค้าเพียวๆ ไม่มีคนหรือสัตว์ในภาพเลย (100% Product B-Roll)\n- เน้นดนตรีประกอบน่าตื่นเต้น ตัดต่อเร้าใจ\n"
        scene_rule = f"2. ทุกซีนต้องเป็นภาพเจาะสินค้า (Product Shot) หรือภาพบรรยากาศสินค้า (Product in Environment) ห้ามวาดมนุษย์หรือตัวละครประหลาดลงในภาพเด็ดขาด ให้ใช้สไตล์ 'Macro photography, cinematic product shot, studio lighting, hyperrealistic, blank product without labels'.\n   - บังคับการเขียน Video Prompt ให้ใช้เทคนิคกล้องหวือหวา (เช่น Dynamic zoom in, Orbit around product, Dolly in, Cinematic pan) เหมือนถ่ายทำโฆษณาสินค้าไฮเอนด์"
        
        if no_voiceover:
            char_rule += "- **ย้ำ: ไม่ต้องคิดบทพูด (Voiceover) เด็ดขาด**\n"
            script_instruction = '3. **ห้ามแต่งบทพูดเด็ดขาด (No Voiceover)** ให้ปล่อยฟิลด์ script ว่างไว้ หรือเขียนเพียงแค่ "[ดนตรีบรรเลงเร้าใจ]"'
            video_voice_instruction = '- **ข้อบังคับเรื่องเสียง:** กำชับไว้ใน Video Prompt เสมอว่า "NO voiceover, NO dialogue, ONLY energetic background music and cinematic sound effects"'
    elif fashion_mode:
        char_rule = f"- โหมดแฟชั่น (ประเภทสินค้า: {fashion_item_type}): เน้นการถ่ายทอดรูปทรง เนื้อผ้า และความพริ้วไหวของสินค้า ไม่เน้นหน้าตานายแบบ/นางแบบ\n- ตัวละครหลัก: {character_type}\n- สีผิว: {character_skin}\n- บุคลิกภาพ/รูปร่าง: {character_traits}\n- **บังคับเนื้อเรื่อง:** กำหนดให้ตัวละครขยับตัวเพื่อโชว์สินค้า เช่น เดินเข้าหากล้อง, หมุนตัว, โพสท่าโชว์สินค้า\n- **ห้ามเปลี่ยนสีและดีไซน์เด็ดขาด:** กำชับใน Image prompt เสมอให้สั่งว่า \"Subject wearing/holding EXACTLY the same product from reference image, maintaining EXACT same color, exact same design, and same texture without any modifications\"\n"
        scene_rule = f"2. ต้องมีฉากที่นำเสนอ \"สินค้าประเภท {fashion_item_type} ชัดๆ\" จำนวน {product_scene_count} ซีน ส่วนซีนที่เหลือให้เป็น \"ฉากเดินแบบ/โพสท่า\" ให้เน้น 'Fashion lookbook, DO NOT focus closely on the face. Focus entirely on the {fashion_item_type} details, textures, and product features'."
        if no_voiceover:
            char_rule += "- **ย้ำ: ไม่ต้องคิดบทพูด (Voiceover) เด็ดขาด**\n"
            script_instruction = '3. **ห้ามแต่งบทพูดเด็ดขาด (No Voiceover)** ให้ปล่อยฟิลด์ script ว่างไว้ หรือเขียนเพียงแค่ "[ดนตรีบรรเลงเร้าใจ]"'
            video_voice_instruction = '- **ข้อบังคับเรื่องเสียง:** กำชับไว้ใน Video Prompt เสมอว่า "NO voiceover, NO dialogue, ONLY energetic background music and cinematic sound effects"\n       - **ท่าทางการเคลื่อนไหวภาพ:** บังคับใน Video prompt ให้ระบุ "Subject modeling the product, walking like a model, spinning around gracefully, posing dynamically to showcase product. Deep depth of field, NO bokeh, NO blurry background, sharp background"'
    else:
        char_rule = f"- ตัวละครหลัก: {character_type}\n- สีผิว: {character_skin}\n- บุคลิกภาพ/รูปร่าง: {character_traits}\n"
        scene_rule = f"2. ต้องมีฉากที่เจาะจงนำเสนอ \"ตัวสินค้าชัดๆ (Product Shot)\" จำนวน {product_scene_count} ซีน ส่วนซีนที่เหลือให้เป็น \"ฉากเล่าเรื่อง/ไลฟ์สไตล์ (Story/Lifestyle)\" ที่มีตัวละครหลัก ในซีนเล่าเรื่องให้เน้น 'Subject interacting naturally with the product, lifestyle photography, expressive facial features, cinematic composition'."

    system_instruction = f"""คุณคือผู้เชี่ยวชาญด้านการทำวิดีโอสั้น (TikTok/Reels) สำหรับ Affiliate Marketing หรือขายของออนไลน์
    งานของคุณคือวิเคราะห์รูปภาพตัวอย่าง และสร้างแผนการทำวิดีโอ (Video Plan) จำนวน {num_scenes} ซีน
    
    ข้อกำหนดของตัวละครและเนื้อเรื่อง:
    - ข้อมูลสินค้าเริ่มต้น: {product_details}
    {char_rule}- สถานที่/ฉากหลัง (Background): {background}
    - ซาวด์เอฟเฟกต์: {sfx_prompt}
    - เสียงผู้พากย์ (Voice Type): {voice_type}
    - อารมณ์น้ำเสียง (Emotion): {voice_emotion}
    
    กฎเหล็กเรื่องข้อความในภาพ (NO TEXT OVERLAY):
    - **ห้าม** ให้เครื่องมือเจนภาพใส่ตัวหนังสือ, ป้ายกำกับ, โลโก้, ลายน้ำ, หรืออักษรใดๆ ลงในภาพเด็ดขาด
    - สินค้าต้องเป็นแบบ Blank Product (ไม่มีฉลากตัวหนังสือ) เสมอ
    
    กติกาการจัดทำ:
    1. ต้องสร้างซีนให้ได้จำนวน {num_scenes} ซีน เป๊ะๆ
    {scene_rule}
    {script_instruction}
    4. เขียนบทพากย์ให้ผู้อ่านสามารถพูดจบได้ภายใน {scene_duration} วินาทีต่อซีน (ไม่สั้นไปและไม่ยาวไป)
    5. เขียน image_prompt เป็นภาษาอังกฤษ เพื่อใช้ **เจนภาพนิ่งด้วย Gemini (Imagen 3) โดยเฉพาะ** 
       - บังคับใส่คำว่า "Vertical 9:16 aspect ratio, pure visual, no typography, blank product, NO text overlays, NO letters, NO labels" ต่อท้ายเสมอ
       - **สำคัญด้านความสมส่วนและความต่อเนื่อง:** ต้องสั่ง "Realistic anatomical proportions, perfectly scaled product compared to human subject, exactly the same character identity across all images"
       - **สไตล์ภาพถ่ายจากมือถือเรียลๆ ร้อยเปอร์เซ็นต:** ให้ระบุลงใน Prompt ทุกซีนว่า "Raw unedited smartphone footage, casual lifestyle, deep depth of field, everything in focus, NO bokeh, NO blurry background, sharp background, natural authentic look" ห้ามเจาะหน้าชัดหลังเบลอเด็ดขาด
       - บรรยายรูปร่าง สี ดีไซน์ ของสินค้าให้ตรงปก ห้ามนำป้ายโฆษณา/ราคามาใส่ใน Prompt เด็ดขาด และห้ามสั่งให้วาดข้อความ
    6. เขียน video_prompt เป็นภาษาอังกฤษ สำหรับ **ภาพเคลื่อนไหวพร้อมเสียง**
       - บังคับใส่คำว่า "NO text overlays, NO letters, pure visual" เสมอ
       - **สไตล์ถ่ายจากมือถือแบบเรียลๆ (Raw/UGC):** บังคับใส่คำว่า "Raw unedited smartphone footage, vertical phone camera, everyday UGC style, realistic handheld subtle shake" ทุกซีน
       - **ฉากหลังต้องชัดทั้งหมดห้ามเบลอ:** บังคับย้ำไปเลยว่า "Extreme deep depth of field, everything in absolute focus, completely sharp background, NO bokeh, NO blurry background" ห้ามวิดีโอออกมาหน้าชัดหลังเบลอเด็ดขาด
       - **ความต่อเนื่องตั้งแต่ต้นจนจบแบบ Extend:** บังคับใส่ตั้งแต่วิดีโอซีน 2 เป็นต้นไปว่า "Continuous seamless extension from the exact previous frame, exact same subject, exact same environment, no cuts, perfectly smooth transition" เพื่อให้ทั้งภาพและบทพากย์เป็นเนื้อเดียวกันที่สุด
       - ระบุ 'Camera motion' และ 'Subject motion' เพิ่มเติมตามบท
       {video_voice_instruction}
    7. ส่งข้อมูลกลับมาในรูปแบบ JSON ตาม Schema ที่กำหนดเท่านั้น ห้ามมีข้อความอื่นปน
    
    รูปแบบ Schema อ้างอิง:
    {VideoPlan.model_json_schema()}
    """
    
    print("กำลังเรียก Gemini ให้คิดสคริปต์แบบกว้างและครอบคลุมทุกมุมมอง...")
    
    # ส่งภาพทั้งหมดเข้าไปพร้อมคำสั่ง
    request_contents = uploaded_images + ["ช่วยวิเคราะห์ข้อมูลสินค้าจากภาพทั้งหมดนี้ และสร้างสคริปต์วิดีโอ TikTok ให้หน่อยครับ ตอบกลับมาเป็นโครงสร้าง JSON ล้วนๆ"]
    
    response = _safe_generate_content(
        client=client,
        model=ai_model,
        contents=request_contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.7,
        )
    )
    
    return response.text

def run_manual_prompt_with_images(prompt: str, image_paths: List[str], ai_model: str = 'gemini-2.5-flash') -> str:
    """ ฟังก์ชันลัดสำหรับโหมดแมนนวล ยิง Prompt เข้า API เพื่อเอา JSON กลับมา """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    import PIL.Image
    uploaded_images = []
    for path in image_paths:
        try:
            img = PIL.Image.open(path)
            uploaded_images.append(img)
        except: pass
            
    response = _safe_generate_content(
        client=client,
        model=ai_model,
        contents=uploaded_images + [prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )
    )
    return response.text

if __name__ == "__main__":
    # วิธีทดสอบ:
    # 1. สร้างโฟลเดอร์ assets/input ก่อน
    # 2. เอาภาพสินค้าไปวางตั้งชื่อว่า sample_product.jpg
    # 3. รันสคริปต์นี้
    
    test_image = "../assets/input/sample_product.jpg"
    
    if os.path.exists(test_image):
        try:
            result_json = generate_video_plan(test_image)
            print("🚀 ผลลัพธ์ (JSON):")
            print(result_json)
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
    else:
        print(f"ไม่พบไฟล์ภาพเตรียมไว้ทดสอบที่ {test_image}")
        print("โปรดนำภาพสินค้าไปวางไว้ที่ตำแหน่งดังกล่าวก่อนรัน")
