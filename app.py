import streamlit as st
import os
import asyncio
from PIL import Image
import json

# นำเข้าฟังก์ชันจากระบบที่เราเขียนไว้
from core.gemini_engine import generate_video_plan, analyze_product_from_images, generate_image_from_prompt
from core.asset_generator import process_all_assets
from core.schema import VideoPlan

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="TikTok Auto Video Generator", page_icon="🎬", layout="wide")

# สร้าง session state เก็บผลลัพธ์วิเคราะห์
if 'product_info' not in st.session_state:
    st.session_state.product_info = None
if 'video_plan_json' not in st.session_state:
    st.session_state.video_plan_json = None
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = {}

st.title("🎬 TikTok Auto Video Generator (Affiliate SaaS)")
st.markdown("อัปโหลดรูปสินค้า 1 รูป แล้วระบบจะคิดสคริปต์ พากย์เสียง และสร้างคลิปวิดีโอปักตะกร้าให้คุณอัตโนมัติ")

# สร้างโฟลเดอร์สำหรับเก็บของ
os.makedirs("../assets/input", exist_ok=True)
os.makedirs("../output", exist_ok=True)

# ส่วนตั้งค่าโหมดและ API Key 
with st.sidebar:
    st.header("⚙️ การตั้งค่าระบบ")
    engine_mode = st.radio("🧠 โหมดการทำงาน", ["👨‍💻 แมนนวล (ไร้ API / สร้าง Prompt ไปก๊อปวาง)", "⚡ อัตโนมัติ (ใช้ API Key)"])
    
    api_key_input = st.text_input("🔑 ใส่ Gemini API Key ของคุณ:", type="password")
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input
        st.success("บันทึก API Key แล้ว")
        
    if engine_mode == "⚡ อัตโนมัติ (ใช้ API Key)":
        if not api_key_input:
            st.warning("⚠️ โปรดใส่ API Key ก่อนใช้งานโหมดอัตโนมัติ")
        st.markdown("**สถานะระบบ:** 🟢 โหมดอัตโนมัติทำงานเต็มรูปแบบ\n(ระบบจะใช้ Gemini API Key ของคุณเชื่อมต่อออโต้)")
    else:
        st.success("🟢 โหมดแมนนวลทำงาน\n(ไร้ลิมิต! ระบบช่วยปรุงโค้ดให้คุณไปก๊อปวาง หรือใช้ปุ่ม API ลัดได้ถ้ากรอก Key ด้านบนแล้ว)")

# ส่วนอัปโหลดภาพสินค้า
uploaded_files = st.file_uploader("📸 อัปโหลดรูปภาพสินค้าของคุณทั้งหมด (รับได้ 1-4 ภาพ) (JPG, PNG, WEBP)", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True)

if uploaded_files:
    if len(uploaded_files) > 4:
        st.error("⚠️ กรุณาอัปโหลดรูปภาพไม่เกิน 4 รูปครับ เพื่อให้ระบบทำงานได้อย่างรวดเร็วและไม่โหลดหนักเกินไป")
    else:
        st.write(f"พบภาพทั้งหมด {len(uploaded_files)} ภาพ")
        # รองรับ Mobile Layout 
        num_cols = min(2, len(uploaded_files))
        cols = st.columns(num_cols) 
        image_paths = []
        
        for i, file in enumerate(uploaded_files):
            image = Image.open(file)
            cols[i % num_cols].image(image, use_container_width=True)
            image_path = f"../assets/input/app_uploaded_product_{i}.jpg"
            rgb_im = image.convert('RGB')
            rgb_im.thumbnail((1080, 1920), Image.Resampling.LANCZOS)
            rgb_im.save(image_path, format="JPEG", quality=95)
            image_paths.append(image_path)
            
        st.markdown("---")
        
        if engine_mode == "⚡ อัตโนมัติ (ใช้ API Key)":
            # ปุ่มกดวิเคราะห์สินค้า (Step 1) โหมดออโต้
            if st.button("🧠 1. วิเคราะห์จุดขายสินค้าและร่างสคริปต์ไอเดีย", use_container_width=True):
                if not os.getenv("GEMINI_API_KEY"):
                    st.error("❌ กรุณาใส่ Gemini API Key ที่แถบด้านซ้ายก่อนครับ")
                else:
                    with st.spinner("AI กำลังวิเคราะห์รูปภาพ..."):
                        try:
                            info = analyze_product_from_images(image_paths)
                            st.session_state.product_info = info
                            st.success("✅ วิเคราะห์ข้อมูลสินค้าสำเร็จ!")
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")
        else:
            # โหมดแมนนวล ข้ามการยิง API วิเคราะห์สินค้า และถือว่ามีข้อมูลเริ่มต้นเลยเพื่อปลดล็อคขั้นตอนถัดไป
            if not st.session_state.product_info:
                st.session_state.product_info = "(โหมดแมนนวล: ระบบจะให้ Gemini วิเคราะห์สินค้าช่วยสำหรับโหมดแมนนวล)"

        # แสดงส่วนตั้งค่าวิดีโอทันทีที่อัปโหลด (ถ้าเป็นแมนนวล) หรือเมื่อวิเคราะห์เสร็จ (ถ้าเป็นออโต้)
        if st.session_state.product_info:
            st.markdown("---")
            st.subheader("⚙️ 2. ปรับแต่งตัวละครและเนื้อเรื่องสำหรับถ่ายทำ")
            
            with st.expander("👤 2.1 - 2.3 ตั้งค่าตัวละครหลัก", expanded=True):
                product_only_mode = st.checkbox("📦 โหมดโชว์เฉพาะสินค้า (ไม่เอาคน/เน้นมุมกล้อง)", value=False)
                fashion_mode = st.checkbox("👗 โหมดแฟชั่นเสื้อผ้า (เน้นตัวละครสวมใส่)", value=False, disabled=product_only_mode)
                
                no_voiceover = False
                if product_only_mode or fashion_mode:
                    no_voiceover = st.checkbox("🚫 ไม่เอาบทพูด (เน้นดนตรีประกอบอย่างเดียว)", value=False)

                if fashion_mode:
                    fashion_item_type = st.selectbox("👗 2.1.2 ประเภทสินค้าแฟชั่น", ["เสื้อ (Tops)", "กางเกง/กระโปรง (Bottoms)", "ชุดเดรส/ชุดเซท (Dress/Sets)", "กระเป๋า (Bags)", "รองเท้า (Shoes)", "หมวก/เครื่องประดับ (Accessories)", "อื่นๆ"])
                    char_options = ["สาวไทย (วัยรุ่น)", "หนุ่มไทย (วัยรุ่น)", "สาวไทย (วัยทำงาน)", "หนุ่มไทย (วัยทำงาน)", "นางแบบอินเตอร์", "นายแบบอินเตอร์", "เด็กเล็ก", "คนแก่", "อื่นๆ"]
                else:
                    fashion_item_type = ""
                    char_options = ["สาวไทย (วัยรุ่น)", "หนุ่มไทย (วัยรุ่น)", "สาวไทย (วัยทำงาน)", "หนุ่มไทย (วัยทำงาน)", "ผู้หญิงทั่วไป", "ผู้ชายทั่วไป", "คนแก่", "ครอบครัวพ่อแม่ลูก", "คู่รัก", "สุนัข", "แมว", "อื่นๆ"]

                char_type = st.selectbox("👤 2.1 เลือกตัวละครหลัก", char_options, index=0, disabled=product_only_mode)
                if char_type == "อื่นๆ":
                    char_type = st.text_input("ระบุตัวละครอื่นๆ:", disabled=product_only_mode)
                    
                no_char_mode = product_only_mode
                
                if no_char_mode:
                    char_type = "ไม่มีตัวละคร"

                char_skin = st.selectbox("🎨 2.2 สีผิวตัวละคร", ["ผิวขาว/สว่าง", "ผิวแทน/น้ำผึ้ง", "ผิวคล้ำเข้ม", "ไม่ระบุ (ให้ AI เลือกเอง)"], disabled=no_char_mode)
                char_bg = st.selectbox("🏞️ 2.3 ฉากหลัง (Background)", ["ไม่ระบุ (อิสระตามเนื้อเรื่อง)", "ธรรมชาติป่าไม้ 🌳", "ทะเล/ชายหาด 🌊", "ภูเขา ⛰️", "ในเมือง/ตึกชิคๆ 🏙️"])
                
            with st.expander("✨ 2.4 - 2.5 บุคลิกภาพและลูกเล่น", expanded=True):
                char_traits = st.multiselect("✨ 2.4 บุคลิกภาพและรูปร่าง (เลือกได้หลายข้อ)", 
                    ["สวยน่ารัก", "เซ็กซี่เย้ายวน", "หน้าอกใหญ่", "หุ่นนายแบบ/นางแบบ", "หล่อเท่สมาร์ท", "แต่งตัวภูมิฐานดูแพง", "ตลกขบขัน", "ร่าเริงสดใส", "ลึกลับน่าค้นหา"],
                    disabled=no_char_mode
                )
                use_sfx = st.radio("🔊 2.5 ใส่ซาวด์เอฟเฟกต์ (Sound Effects) ในสคริปต์?", ["ใส่ซาวด์ (เน้นลูกเล่นตื่นเต้น)", "ไม่ใส่ (เน้นพากย์เสียงอย่างเดียว)"])
                
            with st.expander("🎙️ 2.6 - 2.7 เสียงผู้พากย์", expanded=True):
                voice_type = st.selectbox("🎙️ 2.6 เสียงผู้พากย์ (Voice Type)", ["ไม่ระบุ (สุ่มให้เหมาะสม)", "ผู้หญิง", "ผู้ชาย", "เด็ก", "คนแก่", "หุ่นยนต์/AI", "สัตว์ (เช่น หมา/แมวบรรยาย)"], disabled=no_voiceover)
                voice_emotion = st.selectbox("🎭 2.7 อารมณ์ในการพากย์ (Emotion)", ["ไม่ระบุ (สุ่มให้เหมาะสม)", "ตื่นเต้นเร้าใจ (Energetic)", "ตลกขบขัน/กวนๆ (Funny)", "จริงจัง/น่าเชื่อถือ (Professional)", "กระซิบ/น่าค้นหา (ASMR)", "ดราม่า/ซึ้งกินใจ", "สดใส/อ้อนๆ น่ารัก"], disabled=no_voiceover)
    
            traits_str = ", ".join(char_traits) if char_traits else "ทั่วไป"
            sfx_flag = True if "ใส่" in use_sfx and "ไม่ใส่" not in use_sfx else False
            sfx_prompt = "ให้ใส่เสียง Sound Effects หรือ BGM กวนๆ ตลกๆ หรือตื่นเต้น แทรกในวงเล็บของ script ด้วย เช่น [เสียงตู้ม] หรือ [เสียงหัวเราะ]" if sfx_flag else "ห้ามใส่ Sound Effects ลงในบทพูด ให้ใช้เสียงพากย์ล้วนๆ"
    
            st.markdown("---")
            st.subheader("⚙️ 3. โครงสร้างวิดีโอ (Video Structure)")
            
            with st.expander("🎞️ ตั้งค่าจำนวนฉากและเวลา", expanded=True):
                num_scenes = st.number_input("🎞️ 3.1 จำนวนฉากทั้งหมด (Scenes)", min_value=1, max_value=10, value=3)
                scene_duration = st.number_input("⏱️ 3.2 ความยาว/ฉาก (วินาที)", min_value=3, max_value=30, value=8)
                product_scene_count = st.number_input("📦 3.3 โชว์สินค้าเน้นๆ (ฉาก)", min_value=0, max_value=num_scenes, value=1)
    
            # ปุ่มกดสร้างวิดีโอ (Step 4)
            st.markdown("---")
            if engine_mode == "⚡ อัตโนมัติ (ใช้ API Key)":
                if st.button("🚀 4. อนุมัติสคริปต์และสร้างตารางคิวภาพ (Generate Storyboard ให้อัตโนมัติ)", use_container_width=True):
                    if not os.getenv("GEMINI_API_KEY"):
                        st.error("❌ กรุณาใส่ Gemini API Key ที่แถบด้านซ้ายก่อนครับ")
                    else:
                        with st.status("กำลังทำงาน...", expanded=True) as status:
                            try:
                                st.write(f"🧠 กำลังให้ AI (Gemini) แบ่งสคริปต์เป็น {num_scenes} ช็อต...")
                                json_result = generate_video_plan(
                                    image_paths=image_paths,
                                    product_details=st.session_state.product_info,
                                    character_type=char_type,
                                    character_skin=char_skin,
                                    character_traits=traits_str,
                                    use_sfx=sfx_flag,
                                    num_scenes=num_scenes,
                                    scene_duration=scene_duration,
                                    product_scene_count=product_scene_count,
                                    background=char_bg,
                                    voice_type=voice_type,
                                    voice_emotion=voice_emotion,
                                    no_voiceover=no_voiceover,
                                    fashion_mode=fashion_mode,
                                    fashion_item_type=fashion_item_type
                                )
                                video_plan = VideoPlan.model_validate_json(json_result)
                                st.session_state.video_plan_json = json_result
                                st.session_state.generated_images = {}
                                status.update(label="สร้างตารางแจกแจงซีนเสร็จร้อย! 🎉", state="complete", expanded=False)
                            except Exception as e:
                                status.update(label="เกิดข้อผิดพลาดรุนแรง", state="error")
                                st.error(f"รายละเอียด: {str(e)}")
            else:
                st.subheader("📜 4. สร้าง Master Prompt สำหรับนำไปคุยกับ Gemini Advanced บนเว็บ")
                if st.button("🚀 4.1 คลิกเพื่อสร้างคำสั่ง Prompt อัตโนมัติ", use_container_width=True):
                    
                    script_instruction = '3. คิดบทพากย์ (script) ที่ดึงดูด น่าสนใจ ขายของแบบเนียนๆ โดยต้องสอดคล้องกับ "เสียงผู้พากย์" และ "อารมณ์น้ำเสียง" อย่างเคร่งครัด'
                    video_voice_instruction = f'- **ความต่อเนื่องของเสียงและภาพ:** บังคับให้ใส่คำสั่งเจาะจงเสียงว่า "Include synchronized voiceover narration in {voice_type} voice with {voice_emotion} tone, EXACTLY the same voice identity and vocal characteristics across all clips, character remains identically matched to previous scenes"'
                    
                    if no_char_mode:
                        char_rule = f"- เป็นวิดีโอโชว์สินค้าเพียวๆ ไม่มีคนหรือสัตว์ในภาพเลย (100% Product B-Roll)\n- เน้นดนตรีประกอบน่าตื่นเต้น ตัดต่อเร้าใจ\n"
                        scene_rule = f"2. ทุกซีนต้องเป็นภาพเจาะสินค้า (Product Shot) หรือภาพบรรยากาศสินค้า (Product in Environment) ห้ามวาดมนุษย์หรือตัวละครประหลาดลงในภาพเด็ดขาด\n   - บังคับการเขียน Video Prompt ให้ใช้เทคนิคกล้องหวือหวา (เช่น Dynamic zoom in, Orbit around product, Dolly in, Cinematic pan) เหมือนถ่ายทำโฆษณาสินค้าไฮเอนด์"
                        if no_voiceover:
                            script_instruction = '3. **ห้ามแต่งบทพูดเด็ดขาด (No Voiceover)** ให้ปล่อยฟิลด์ script ว่างไว้ หรือเขียนเพียงแค่ "[ดนตรีบรรเลงเร้าใจ]"'
                            video_voice_instruction = '- **ข้อบังคับเรื่องเสียง:** กำชับไว้ใน Video Prompt เสมอว่า "NO voiceover, NO dialogue, ONLY energetic background music and cinematic sound effects"'
                            char_rule += "- **ย้ำ: ไม่ต้องคิดบทพูด (Voiceover) เด็ดขาด**\n"
                    elif fashion_mode:
                        char_rule = f"- โหมดแฟชั่น (ประเภทสินค้า: {fashion_item_type}): เน้นการถ่ายทอดรูปทรง เนื้อผ้า และความพริ้วไหวของสินค้า ไม่เน้นหน้าตานายแบบ/นางแบบ\n- ตัวละครหลัก: {char_type}\n- สีผิว: {char_skin}\n- บุคลิกภาพ/รูปร่าง: {traits_str}\n- **บังคับเนื้อเรื่อง:** กำหนดให้ตัวละครขยับตัวเพื่อโชว์สินค้า เช่น เดินเข้าหากล้อง, หมุนตัว, สะบัดชายเสื้อ/กระโปรง, เดินเหลียวหลัง\n- **ห้ามเปลี่ยนสีและดีไซน์เด็ดขาด:** กำชับใน Image prompt เสมอให้สั่งว่า \"Subject wearing/holding EXACTLY the same product from reference image, maintaining EXACT same color, exact same design, and same texture without any modifications\"\n"
                        scene_rule = f"2. ต้องมีฉากที่นำเสนอ \"สินค้าประเภท {fashion_item_type} ชัดๆ\" จำนวน {product_scene_count} ซีน ส่วนซีนที่เหลือให้เป็น \"ฉากเดินแบบ/โพสท่า\" ให้เน้น 'Fashion lookbook, DO NOT focus closely on the face. Focus entirely on the {fashion_item_type} details, textures, and product features'."
                        if no_voiceover:
                            script_instruction = '3. **ห้ามแต่งบทพูดเด็ดขาด (No Voiceover)** ให้ปล่อยฟิลด์ script ว่างไว้ หรือเขียนเพียงแค่ "[ดนตรีบรรเลงเร้าใจ]"'
                            video_voice_instruction = '- **ข้อบังคับเรื่องเสียง:** กำชับไว้ใน Video Prompt เสมอว่า "NO voiceover, NO dialogue, ONLY energetic background music and cinematic sound effects"\n   - **ท่าทางการเคลื่อนไหวภาพ:** สั่งกำกับใน Video prompt เสมอให้ "Subject modeling the product, walking like a runway model, spinning around gracefully, dynamic posing to showcase product. Deep depth of field, NO bokeh, NO blurry background, sharp background"'
                            char_rule += "- **ย้ำ: ไม่ต้องคิดบทพูด (Voiceover) เด็ดขาด**\n"
                    else:
                        char_rule = f"- ตัวละครหลัก: {char_type}\n- สีผิว: {char_skin}\n- บุคลิกภาพ/รูปร่าง: {traits_str}\n"
                        scene_rule = f"2. ต้องมีฉากที่เจาะจงนำเสนอ \"ตัวสินค้าชัดๆ (Product Shot)\" จำนวน {product_scene_count} ซีน ส่วนซีนที่เหลือให้เป็น \"ฉากเล่าเรื่อง/ไลฟ์สไตล์ (Story/Lifestyle)\" ที่มีตัวละครหลัก"

                    master_prompt = f"""คุณคือผู้เชี่ยวชาญด้านการทำวิดีโอสั้น (TikTok/Reels) สำหรับ Affiliate Marketing หรือขายของออนไลน์
งานของคุณคือวิเคราะห์ 'ภาพสินค้า' ที่ฉันแนบมานี้ และสร้างแผนการทำวิดีโอ (Video Plan) จำนวน {num_scenes} ซีน

ข้อกำหนดของตัวละครและเนื้อเรื่อง:
- ข้อมูลสินค้าเริ่มต้น: {st.session_state.product_info}
{char_rule}- สถานที่/ฉากหลัง (Background): {char_bg}
- ซาวด์เอฟเฟกต์: {sfx_prompt}
- เสียงผู้พากย์ (Voice Type): {voice_type}
- อารมณ์น้ำเสียง (Emotion): {voice_emotion}

กติกาการจัดทำ:
1. ต้องสร้างซีนให้ได้จำนวน {num_scenes} ซีน เป๊ะๆ
{scene_rule}
{script_instruction}
4. เขียนบทพากย์ให้สามารถพูดจบได้ภายใน {scene_duration} วินาทีต่อซีน 
5. เขียน image_prompt เป็นภาษาอังกฤษ เพื่อใช้ **เจนภาพนิ่งด้วย Gemini (Imagen 3)**
   - บังคับให้ใส่: "Vertical 9:16 aspect ratio, NO text overlays, NO typography"
   - **กฎความสมส่วนหน้าตาและสินค้า:** ให้สั่งย้ำคำว่า "Realistic anatomical proportions, product size is naturally scaled compared to character, exactly the SAME person identity across all scenes" เพื่อให้ภาพทุกซีนเป็นคนๆเดียวกันและขนาดสินค้าไม่ผิดเพี้ยน
   - **สไตล์ภาพถ่ายสมจริง:** ให้ใส่คำว่า "Shot on modern smartphone, casual everyday lifestyle photo, deep depth of field (f/8.0), everything in focus, NO bokeh, NO blurry background, sharp background, natural authentic look" เสมอ เพื่อไม่ให้ภาพดูเจาะจงหน้าชัดหลังเบลอเกินจริง
   - บรรยายแสงเงา บรรยากาศ มุมกล้อง (Lighting, Mood, Camera angle) ให้สวยงามสมจริง ห้ามสั่งให้วาดป้ายราคา/ข้อความ
6. เขียน video_prompt เป็นภาษาอังกฤษ สำหรับ **เจนวนิเมชัน+เสียง บน Google Labs Flow**
   - การขยับ: เน้นสั่งเฉพาะ 'Camera motion' และ 'Subject motion' อย่างกระชับ พร้อมสั่ง "NO text overlays"
   {video_voice_instruction}
7. ส่งข้อมูลกลับมาเป็นโค้ด JSON ก้อนเดียวเท่านั้น ห้ามมีคำอธิบายเพิ่มเติม

รูปแบบโครงสร้าง JSON ที่ต้องตอบกลับ:
{VideoPlan.model_json_schema()}"""
                    st.info("ขั้นตอนการทำ: 1) ถ่ายรูปสินค้าแนบขึ้นเว็บ Gemini 2) ก๊อปปี้คลิปบอร์ดข้อความด้านล่าง (มุมขวาบนของกล่องดำ) แปะลงช่องแชท 3) เคาะ Enter ให้มันคิดบท!")
                    st.markdown('<a href="https://gemini.google.com/app" target="_blank" style="display: block; width: 100%; text-align: center; padding: 0.5rem 1rem; background-color: #262730; color: white; text-decoration: none; border-radius: 0.5rem; border: 1px solid rgba(250, 250, 250, 0.2); margin-bottom: 1rem; font-family: sans-serif;">🌐 คลิกเปิดหน้าต่างเว็บ Gemini Advanced ทิ้งไว้ได้เลย</a>', unsafe_allow_html=True)
                    st.code(master_prompt, language="text")
                    
                    if os.getenv("GEMINI_API_KEY"):
                        st.markdown("---")
                        st.success("💡 **ตรวจพบ API Key ในระบบ:** กำลังลัดขั้นตอน ส่ง Prompt นี้ให้ Gemini ร่างบทให้คุณอัตโนมัติ...")
                        with st.spinner("กำลังรับข้อมูลสคริปต์จาก AI... (รอสักครู่)"):
                            try:
                                from core.gemini_engine import run_manual_prompt_with_images
                                result_json = run_manual_prompt_with_images(master_prompt, image_paths)
                                st.session_state.demo_pasted_json = result_json
                                st.success("✅ ได้รับบทมาเรียบร้อย! ระบบนำโค้ดไปวางในกล่อง 4.5 ด้านล่างให้แล้ว เลื่อนไปกดปุ่มประมวลผลต่อได้เลยครับ")
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
                
                st.markdown("---")
                st.subheader("📥 4.5 วางผลลัพธ์จาก Gemini ลงที่นี่")
                default_json = st.session_state.get('demo_pasted_json', '')
                pasted_json = st.text_area("เมื่อหน้าเว็บ Gemini พิมพ์บทให้เสร็จ ให้ก๊อปปี้ 'โค้ด JSON' ทั้งหมด นำมาประเคนไว้ในช่องนี้ครับ:", value=default_json, height=150)
                if st.button("✅ ประมวลผลตารางสคริปต์ (Render Storyboard)", use_container_width=True):
                    if pasted_json.strip():
                        try:
                            # ล้างโค้ด Markdown block ออกเผื่อผู้ใช้ก๊อปมาติด ```json 
                            cleaned_json = pasted_json.replace("```json", "").replace("```", "").strip()
                            video_plan = VideoPlan.model_validate_json(cleaned_json)
                            st.session_state.video_plan_json = cleaned_json
                            st.session_state.generated_images = {}
                            st.success(f"✅ ประมวลผลโค้ดแยกช็อตสำเร็จ! (สินค้า: {video_plan.product_name})")
                        except Exception as e:
                            st.error(f"❌ รูปแบบ JSON ไม่ถูกต้อง กรุณาเช็คว่าก๊อปปี้โค้ดมาครบทุกบรรทัดตั้งแต่ปีกกาเปิดยันปิดหรือไม่ (รายละเอียด: {e})")
                    else:
                        st.warning("⚠️ กรุณาวางโค้ด JSON ก่อนกดปุ่มครับ")

        # ส่วนที่ดึงตารางและขั้นตอนหลังจากโหลด JSON ยัดเข้า session_state เรียบร้อย
        if st.session_state.video_plan_json:
            try:
                video_plan = VideoPlan.model_validate_json(st.session_state.video_plan_json)
                
                # โชว์แท็บจัดกลุ่มตามซีน
                st.markdown("---")
                st.subheader("📋 5. แผนการทำวิดีโอรายฉาก (Storyboard & Prompts)")
                st.info("แตะขวา/ซ้าย ที่แท็บเพื่อดูรายละเอียดและอัปโหลดวิดีโอทีละซีน👇")
                
                if engine_mode == "⚡ อัตโนมัติ (ใช้ API Key)":
                    if st.button("✨ เริ่มเจนภาพนิ่งทุกซีนอัตโนมัติ (Imagen 3)", use_container_width=True):
                        with st.spinner("กำลังวาดภาพ... (อาจใช้เวลาสักครู่)"):
                            st.session_state.generated_images = {}
                            for scene in video_plan.scenes:
                                img_path = f"../assets/input/scene_{scene.scene_number}_generated.jpg"
                                st.write(f"กำลังเจนภาพซีนที่ {scene.scene_number}...")
                                success, error_msg = generate_image_from_prompt(scene.image_prompt, img_path)
                                
                                st.session_state.generated_images[scene.scene_number] = img_path
                                if not success:
                                    st.warning(f"ซีนที่ {scene.scene_number} วาดภาพล้มเหลว: {error_msg}")
                else:
                    st.markdown("*(โหมดแมนนวล: ก๊อปปี้ข้อความไปเจนรูปและวิดีโอบนเว็บได้เลยครับ)*")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        st.markdown('<a href="https://gemini.google.com/app" target="_blank" style="display: block; width: 100%; text-align: center; padding: 0.5rem 1rem; background-color: #262730; color: white; text-decoration: none; border-radius: 0.5rem; border: 1px solid rgba(250, 250, 250, 0.2); font-family: sans-serif;">🌐 เปิดเว็บ Gemini (รูป)</a>', unsafe_allow_html=True)
                    with col_btn2:
                        st.markdown('<a href="https://labs.google/fx/tools/flow" target="_blank" style="display: block; width: 100%; text-align: center; padding: 0.5rem 1rem; background-color: #262730; color: white; text-decoration: none; border-radius: 0.5rem; border: 1px solid rgba(250, 250, 250, 0.2); font-family: sans-serif;">🎥 เปิดเว็บ Labs Flow (วิดีโอ)</a>', unsafe_allow_html=True)

                os.makedirs("../assets/video", exist_ok=True)
                os.makedirs("../assets/audio", exist_ok=True)
                
                # ใช้ระบบ Tabs เป็นมิตรกับมือถือและลดการไถจอ
                scene_tabs = st.tabs([f"🎬 ซีน {scene.scene_number}" for scene in video_plan.scenes])
                
                for i, scene in enumerate(video_plan.scenes):
                    with scene_tabs[i]:
                        st.markdown(f"**⏱️ เวลา:** {scene.timecode_start} - {scene.timecode_end}")
                        st.markdown(f"**🗣️ บทพากย์/เสียง:** {scene.script}")
                        
                        st.markdown("---")
                        st.write("🖼️ **1. นำพรอมต์นี้ไปสร้างรูป (Image Prompt):**")
                        st.code(scene.image_prompt, language="text")
                        
                        if st.session_state.generated_images and scene.scene_number in st.session_state.generated_images:
                            img_path = st.session_state.generated_images[scene.scene_number]
                            if os.path.exists(img_path):
                                st.image(Image.open(img_path), caption=f"ภาพที่วาดได้ (ซีน {scene.scene_number})", use_container_width=True)
                                
                        st.markdown("---")
                        st.write("🎥 **2. นำรูปภาพและพรอมต์นี้ไปทำภาพเคลื่อนไหว:**")
                        st.code(f"{scene.video_prompt}\n(Voiceover: {scene.script})", language="text")
                        
            except Exception as e:
                st.error(f"ข้อผิดพลาดระหว่างแสดงผลสคริปต์: {e}")
                
        st.markdown("---")
        st.subheader("📝 6. ข้อมูลสำหรับโพสต์ TikTok (Caption & Hashtags)")
        st.write("อัปโหลดรูปภาพสินค้าใหม่ เพื่อให้ AI ตีความจุดขายและเขียนแคปชั่น แฮชแท็ก ป้ายกำกับต่างๆ สำหรับโพสต์ลง TikTok โดยเฉพาะ (ไม่ต้องสนใจรูปด้านบน)")
        
        post_uploaded_files = st.file_uploader("📸 อัปโหลดรูปภาพสำหรับหน้าโพสต์ (1-4 ภาพ)", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True, key="post_upload")
        
        if st.button("✨ วิเคราะห์ภาพและสร้างแคปชั่นโพสต์", use_container_width=True):
            if not post_uploaded_files:
                st.warning("⚠️ กรุณาอัปโหลดรูปภาพสินค้าก่อนครับ")
            elif not os.getenv("GEMINI_API_KEY"):
                st.warning("⚠️ กรุณาใส่ Gemini API Key (ที่แถบตั้งค่าด้านซ้าย) เพื่อเริ่มใช้งาน")
            else:
                with st.spinner("กำลังให้เซียนการตลาด AI วิเคราะห์ภาพและคิดแคปชั่น..."):
                    try:
                        os.makedirs("../assets/input", exist_ok=True)
                        post_img_paths = []
                        for idx, f in enumerate(post_uploaded_files):
                            path = f"../assets/input/post_img_{idx}.jpg"
                            with open(path, "wb") as pf:
                                pf.write(f.read())
                            post_img_paths.append(path)
                        
                        from core.gemini_engine import analyze_product_from_images
                        result_json = analyze_product_from_images(post_img_paths)
                        st.session_state.custom_post_json = result_json
                        st.success("✅ ร่างแคปชั่นเสร็จสมบูรณ์!")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการวิเคราะห์: {e}")
                        
        if st.session_state.get('custom_post_json'):
            try:
                import json
                post_data = json.loads(st.session_state.custom_post_json)
                
                st.info(f"**📌 รายละเอียดสินค้า:**\n{post_data.get('product_details', '')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"**💬 ข้อความพาดหัวคลิป (Overlay Text):**\n{post_data.get('overlay_text', '')}")
                    st.warning(f"**🛒 ชื่อปุ่มตะกร้า/ลิงก์:**\n{post_data.get('link_title', '')}")
                with col2:
                    st.info(f"**📝 แคปชั่นโพสต์ขาย (Caption):**\n{post_data.get('post_caption', '')}")
                    st.write(f"**#️⃣ แฮชแท็ก:**\n{post_data.get('hashtags', '')}")
            except Exception as e:
                st.error("ข้อมูลที่ตอบกลับมาไม่ใช่รูปแบบ JSON")
                with st.expander("ดูข้อความดิบจาก AI"):
                    st.write(st.session_state.custom_post_json)
