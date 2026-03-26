import os
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from core.schema import VideoScene, VideoPlan
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

def assemble_tiktok_video(plan: VideoPlan, output_path: str = "../output/final_video.mp4"):
    """
    ฟังก์ชันสำหรับนำไฟล์วิดีโอ (ซีนต่างๆ) ไฟล์เสียงพากย์ และสร้างซับไตเติ้ล
    นำมาประกอบร่างกันเป็นวิดีโอ 1 ตัวความยาวแนวตั้ง (9:16)
    """
    
    print(f"กำลังเริ่มตัดต่อวิดีโอสินค้า: {plan.product_name}")
    print("--------------------------------------------------")
    
    clips_to_concat = []
    opened_clips = [] # เก็บ clip ทั้งหมดไว้ปิดตอนท้าย ป้องกัน WinError 32
    
    for scene in plan.scenes:
        print(f"กำลังประมวลผลซีนที่ {scene.scene_number}...")
        
        video_file = f"../assets/video/scene_{scene.scene_number}.mp4"
        image_file = f"../assets/images/scene_{scene.scene_number}.jpg"
        
        # 1. โหลดคลิปวิดีโอภาพเคลื่อนไหว (ซึ่งมีเสียงติดมาด้วยแล้ว) หรือใช้ภาพนิ่งแทน
        try:
            if os.path.exists(video_file):
                v_clip = VideoFileClip(video_file)
                opened_clips.append(v_clip)
            elif os.path.exists(image_file):
                from moviepy.editor import ImageClip
                v_clip = ImageClip(image_file)
                opened_clips.append(v_clip)
                v_clip = v_clip.resize(width=1080)
                v_clip = v_clip.on_color(size=(1080, 1920), color=(0,0,0), pos='center')
                # กำหนดความยาวให้ภาพนิ่งประมาณ 8 วินาที เพราะไม่มีเสียงให้ยึด
                v_clip = v_clip.set_duration(8)
            else:
                print(f"⚠️ ข้ามซีนที่ {scene.scene_number} เนื่องจากไม่มีทั้งวิดีโอและรูปภาพ")
                continue
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการโหลดภาพ/วิดีโอ: {e}")
            continue
            
        # (เราไม่ต้องโหลดเสียงแยกแล้ว เพราะเสียงฝังมากับวิดีโอจาก Flow แล้ว)
            
        # เก็บเข้าลิสต์สำหรับเอาไปต่อกัน
        clips_to_concat.append(v_clip)
            
    # 5. นำทุกซีนมาต่อกัน
    if clips_to_concat:
        print("กำลังรวบรวมซีนทั้งหมดเข้าด้วยกัน (Concatenating)...")
        final_tiktok_video = concatenate_videoclips(clips_to_concat, method="compose")
        opened_clips.append(final_tiktok_video)
        
        print(f"กำลัง Render วิดีโอไปที่ {output_path} (อาจใช้เวลาสักครู่)")
        try:
            final_tiktok_video.write_videofile(
                output_path, 
                fps=30, 
                codec="libx264", 
                audio_codec="aac",
                preset="fast",
                bitrate="8000k",
                threads=4
            )
            print("✅ ตัดต่อเสร็จสิ้น!")
        finally:
            # ปิด clip ทั้งหมดคืนให้ OS ป้องกัน WinError 32
            for c in opened_clips:
                try:
                    c.close()
                except:
                    pass
    else:
        print("❌ ไม่มีซีนใดถูกดึงมาประมวลผลได้เลย (โปรดตรวจสอบโฟลเดอร์ assets)")

if __name__ == "__main__":
    print("นี่คือไฟล์ระบบตัดต่อ (MoviePy) ถูกออกแบบมาให้รับ JSON Plan จากระบบหลักมาใช้งาน")
