from io import BytesIO
from math import ceil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont, features
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader

BLUE='#006DA8'
INK='#203247'
MUTED='#60768A'

def render_trip_pdf(output, trip, photos, load_image):
    # Pillow RAQM shapes Thai marks correctly; rasterize metadata at 3x for print.
    if not features.check_feature('raqm'):
        raise RuntimeError('PDF Thai shaping requires Pillow RAQM support')
    font_path=Path('/usr/share/fonts/truetype/tlwg/Loma.ttf')
    if not font_path.exists():
        raise RuntimeError('PDF Thai font is not installed')
    width,height=landscape(A4)
    canvas=Canvas(output,pagesize=(width,height),pageCompression=1)
    canvas.setTitle(f"Container Loading - {trip['truck_id']}")
    canvas.setAuthor('CJ Logistics')
    def text(value,x,y,max_width,size=11,color=INK):
        value=' '.join(str(value).split())
        font=ImageFont.truetype(str(font_path),round(size*3),layout_engine=ImageFont.Layout.RAQM)
        probe=ImageDraw.Draw(Image.new('RGB',(1,1)))
        while value and probe.textlength(value,font=font)>max_width*3:
            value=value[:-2].rstrip()+ '…' if len(value)>2 else ''
        if not value:
            return
        box=probe.textbbox((0,0),value,font=font)
        tile=Image.new('RGBA',(max(1,ceil(box[2]-box[0])+6),max(1,box[3]-box[1]+6)),(255,255,255,0))
        ImageDraw.Draw(tile).text((3-box[0],3-box[1]),value,font=font,fill=color)
        canvas.drawImage(ImageReader(tile),x,y-tile.height/3,width=tile.width/3,height=tile.height/3,mask='auto')
    pages=max(1,ceil(len(photos)/6))
    generated=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M')
    logo=Path(__file__).resolve().parent.parent/'assets'/'cj-logistics.png'
    for page in range(pages):
        canvas.setFillColor(white);canvas.rect(0,0,width,height,fill=1,stroke=0)
        canvas.setFillColor(HexColor('#0080C6'));canvas.rect(0,height-5,width*.76,5,fill=1,stroke=0)
        canvas.setFillColor(HexColor('#E42F44'));canvas.rect(width*.76,height-5,width*.12,5,fill=1,stroke=0)
        canvas.setFillColor(HexColor('#EC8922'));canvas.rect(width*.88,height-5,width*.12,5,fill=1,stroke=0)
        canvas.drawImage(str(logo),28,height-63,width=88,height=36,preserveAspectRatio=True,anchor='c',mask='auto')
        canvas.setFillColor(HexColor(INK));canvas.setFont('Helvetica-Bold',19);canvas.drawString(132,height-40,'CONTAINER LOADING')
        canvas.setFillColor(HexColor(MUTED));canvas.setFont('Helvetica',9);canvas.drawString(133,height-56,'TRIP PHOTO REPORT  /  CJ LOGISTICS')
        canvas.setFont('Helvetica-Bold',11);canvas.drawRightString(width-28,height-39,f'{len(photos)} PHOTOS')
        canvas.setFont('Helvetica',8);canvas.drawRightString(width-28,height-55,trip['status'])
        canvas.setFillColor(HexColor('#F2F7FB'));canvas.roundRect(28,height-132,width-56,58,8,fill=1,stroke=0)
        shipment=' / '.join(item['number'] for item in trip['shipments'])
        stores=' / '.join(f"{item['store_code']} {item['store_name']}" for item in trip['shipments'])
        text(f"ทะเบียน: {trip['truck_id']} | {trip['truck_type']}",40,height-84,250)
        text(f"Shipment: {shipment}",305,height-84,width-345)
        text(f"ผู้บันทึก: {trip['worker_name']}",40,height-108,250)
        text(f"Store: {stores}",305,height-108,width-345)
        gap=12;cell_w=(width-56-2*gap)/3;cell_h=(height-194-gap)/2;top=height-146
        for position,photo in enumerate(photos[page*6:(page+1)*6]):
            x=28+(position%3)*(cell_w+gap);y=top-(position//3)*(cell_h+gap)-cell_h
            canvas.setStrokeColor(HexColor('#DCE7EF'));canvas.setFillColor(HexColor('#F8FAFC'));canvas.roundRect(x,y,cell_w,cell_h,7,fill=1,stroke=1)
            with Image.open(BytesIO(load_image(photo))) as original:
                image=original.convert('RGB');image.thumbnail((1200,1200),Image.Resampling.LANCZOS)
                compressed=BytesIO();image.save(compressed,'JPEG',quality=78,optimize=True)
                factor=min((cell_w-16)/image.width,(cell_h-36)/image.height)
                iw,ih=image.width*factor,image.height*factor
                compressed.seek(0)
                canvas.drawImage(ImageReader(compressed),x+(cell_w-iw)/2,y+28+(cell_h-36-ih)/2,width=iw,height=ih)
            canvas.setFillColor(HexColor(BLUE));canvas.setFont('Helvetica-Bold',9);canvas.drawString(x+10,y+11,f'PHOTO {page*6+position+1:03d}')
            canvas.setFillColor(HexColor(MUTED));canvas.setFont('Helvetica',7)
            uploaded=photo['uploaded_at'].astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M')
            canvas.drawRightString(x+cell_w-10,y+11,uploaded+(' / ARCHIVE' if photo['archived_at'] else ''))
        canvas.setStrokeColor(HexColor('#DCE7EF'));canvas.line(28,34,width-28,34)
        canvas.setFillColor(HexColor(MUTED));canvas.setFont('Helvetica',7);canvas.drawString(28,21,f"TRIP {trip['id']}  |  Generated {generated} ICT")
        canvas.drawRightString(width-28,21,f'PAGE {page+1} / {pages}')
        canvas.showPage()
    canvas.save()
