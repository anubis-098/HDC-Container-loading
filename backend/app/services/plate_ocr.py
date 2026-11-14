import os
import re
import subprocess
from io import BytesIO
from PIL import Image, ImageOps, ImageFilter
from threading import BoundedSemaphore
from fastapi import HTTPException
from app.services.images import normalize_image

_slots = BoundedSemaphore(2)

def plate_candidates(text):
    text = text.translate(str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789'))
    results = []
    for line in text.splitlines():
        line = re.sub(r'[–—−]', '-', line)
        for pattern in (r'(?<!\d)(\d{2,3})\s*[- ]\s*(\d{4})(?!\d)', r'(?<![ก-ฮ\d])([0-9]?\s*[ก-ฮ](?:\s*[ก-ฮ]){0,2})\s*[- ]?\s*(\d{1,4})(?!\d)'):
            for match in re.finditer(pattern, line):
                prefix = re.sub(r'\s+', '', match[1])
                candidate = f'{prefix}-{match[2]}'
                if candidate not in results:
                    results.append(candidate)
    return results[:8]

def recognize_plate(content):
    data, _ = normalize_image(content)
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'ระบบอ่านทะเบียนกำลังทำงาน กรุณาลองใหม่')
    try:
        def recognize(image_data, mode):
            result = subprocess.run(['tesseract','stdin','stdout','-l','tha+eng','--psm',mode], input=image_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=True, env={**os.environ, 'OMP_THREAD_LIMIT':'1'})
            return result.stdout.decode('utf-8', errors='replace')[:2000]

        # Keep the full image as the first pass; cropped fallback assumes the
        # camera guide contains a horizontal plate with its province below.
        text = recognize(data, '6')
        candidates = plate_candidates(text)
        if not candidates:
            with Image.open(BytesIO(data)) as original:
                gray = ImageOps.autocontrast(original.convert('L'))
                width, height = gray.size
                plate_line = gray.crop((round(width * .04), round(height * .06), round(width * .96), round(height * .61)))
                target_width = min(2000, max(1200, plate_line.width))
                plate_line = plate_line.resize((target_width, round(plate_line.height * target_width / plate_line.width)), Image.Resampling.LANCZOS)
                plate_line = plate_line.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=3))
                plate_line = ImageOps.expand(plate_line, border=24, fill=255)
                buffer = BytesIO()
                plate_line.save(buffer, format='PNG')
            fallback = recognize(buffer.getvalue(), '7')
            candidates = plate_candidates(fallback)
            text = (text + '\n' + fallback)[:4000]
        return {'candidates': candidates, 'text': text}
    except FileNotFoundError:
        raise HTTPException(503, 'ยังไม่ได้ติดตั้ง OCR กรุณา build API ใหม่')
    except subprocess.TimeoutExpired:
        raise HTTPException(504, 'อ่านภาพนานเกินไป กรุณาถ่ายเฉพาะป้ายทะเบียนให้ชัดขึ้น')
    except subprocess.CalledProcessError:
        raise HTTPException(503, 'ระบบอ่านทะเบียนไม่พร้อม กรุณาพิมพ์ทะเบียนเอง')
    finally:
        _slots.release()
