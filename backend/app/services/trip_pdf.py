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
    new_structure=trip.get('structure_version')==2
    pallets=trip.get('pallets',[])
    def wrapped(value,max_width,size=10):
        font=ImageFont.truetype(str(font_path),round(size*3),layout_engine=ImageFont.Layout.RAQM)
        probe=ImageDraw.Draw(Image.new('RGB',(1,1)))
        lines=[];line=''
        for char in str(value):
            if line and probe.textlength(line+char,font=font)>max_width*3:
                lines.append(line);line=''
            line+=char
        if line: lines.append(line)
        return lines or ['-']
    appendix=[]
    for pallet in pallets if new_structure else []:
        for line in wrapped(f"Pallet {pallet['number']} | Store {pallet['store_code']} : {pallet['store_name']}",width-80,11):
            appendix.append(('header',line))
        for index,order in enumerate(pallet['orders'],1):
            for line in wrapped(f'Order No. {index}: {order}',width-96):
                appendix.append(('order',line))
        if not pallet['orders']: appendix.append(('order','Order No.: -'))
        appendix.append(('space',''))
    appendix_pages=[];current=[]
    for item in appendix:
        if len(current)>=24 or (item[0]=='header' and len(current)>21):
            appendix_pages.append(current);current=[]
        current.append(item)
    if current: appendix_pages.append(current)
    photo_pages=max(1,ceil(len(photos)/6))
    pages=photo_pages+len(appendix_pages)
    generated=datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M')
    logo=Path(__file__).resolve().parent.parent/'assets'/'cj-logistics.png'
    for page in range(photo_pages):
        canvas.setFillColor(white);canvas.rect(0,0,width,height,fill=1,stroke=0)
        canvas.setFillColor(HexColor('#0080C6'));canvas.rect(0,height-5,width*.76,5,fill=1,stroke=0)
        canvas.setFillColor(HexColor('#E42F44'));canvas.rect(width*.76,height-5,width*.12,5,fill=1,stroke=0)
        canvas.setFillColor(HexColor('#EC8922'));canvas.rect(width*.88,height-5,width*.12,5,fill=1,stroke=0)
        canvas.drawImage(str(logo),28,height-63,width=88,height=36,preserveAspectRatio=True,anchor='c',mask='auto')
        canvas.setFillColor(HexColor(INK));canvas.setFont('Helvetica-Bold',19);canvas.drawString(132,height-40,'CONTAINER LOADING')
        canvas.setFillColor(HexColor(MUTED));canvas.setFont('Helvetica',9);canvas.drawString(133,height-56,'TRIP PHOTO REPORT  /  CJ LOGISTICS')
        canvas.setFont('Helvetica-Bold',11);canvas.drawRightString(width-28,height-39,f'{len(photos)} PHOTOS')
        canvas.setFont('Helvetica',8);canvas.drawRightString(width-28,height-55,trip['status'])
        canvas.setFillColor(HexColor('#F2F7FB'));canvas.roundRect(28,height-151,width-56,77,8,fill=1,stroke=0)
        shipment=' / '.join(item['number'] for item in trip['shipments'])
        stores=' / '.join(f"{item['store_code']} {item['store_name']}" for item in trip['shipments'])
        if new_structure:
            shipment=f"{len(pallets)} Pallets | {len({o for p in pallets for o in p['orders']})} Orders"
            stores=' / '.join(dict.fromkeys(p['store_code'] for p in pallets))
        text(f"ทะเบียน: {trip['truck_id']} | {trip['truck_type']}",40,height-84,250)
        text(shipment if new_structure else f"Shipment: {shipment}",305,height-84,width-345)
        text(f"ผู้บันทึก: {trip['worker_name']}",40,height-108,250)
        text(f"Store: {stores}",305,height-108,width-345)
        orders=list(dict.fromkeys(order for pallet in pallets for order in pallet.get('orders',[])))
        text('Order No.: '+(' / '.join(orders) or '-'),40,height-132,width-80,size=9)
        gap=12;cell_w=(width-56-2*gap)/3;cell_h=(height-213-gap)/2;top=height-165
        for position,photo in enumerate(photos[page*6:(page+1)*6]):
            x=28+(position%3)*(cell_w+gap);y=top-(position//3)*(cell_h+gap)-cell_h
            canvas.setStrokeColor(HexColor('#DCE7EF'));canvas.setFillColor(HexColor('#F8FAFC'));canvas.roundRect(x,y,cell_w,cell_h,7,fill=1,stroke=1)
            with Image.open(BytesIO(load_image(photo))) as original:
                image=original.convert('RGB');image.thumbnail((1200,1200),Image.Resampling.LANCZOS)
                compressed=BytesIO();image.save(compressed,'JPEG',quality=78,optimize=True)
                caption_space=64 if new_structure else 36
                factor=min((cell_w-16)/image.width,(cell_h-caption_space)/image.height)
                iw,ih=image.width*factor,image.height*factor
                compressed.seek(0)
                canvas.drawImage(ImageReader(compressed),x+(cell_w-iw)/2,y+(56 if new_structure else 28)+(cell_h-caption_space-ih)/2,width=iw,height=ih)
            if new_structure:
                pallet=next((p for p in pallets if p['id']==photo['pallet_id']),None)
                text(f"Pallet {pallet['number']} | Store {pallet['store_code']}" if pallet else 'Trip overview',x+10,y+46,cell_w-20,size=8)
                text('Order No.: '+(' / '.join(pallet['orders']) if pallet and pallet['orders'] else '-'),x+10,y+32,cell_w-20,size=8)
            canvas.setFillColor(HexColor(BLUE));canvas.setFont('Helvetica-Bold',9);canvas.drawString(x+10,y+11,f'PHOTO {page*6+position+1:03d}')
            canvas.setFillColor(HexColor(MUTED));canvas.setFont('Helvetica',7)
            uploaded=photo['uploaded_at'].astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M')
            canvas.drawRightString(x+cell_w-10,y+11,uploaded+(' / ARCHIVE' if photo['archived_at'] else ''))
        canvas.setStrokeColor(HexColor('#DCE7EF'));canvas.line(28,34,width-28,34)
        canvas.setFillColor(HexColor(MUTED));canvas.setFont('Helvetica',7);canvas.drawString(28,21,f"TRIP {trip['id']}  |  Generated {generated} ICT")
        canvas.drawRightString(width-28,21,f'PAGE {page+1} / {pages}')
        canvas.showPage()
    for number,lines in enumerate(appendix_pages,photo_pages+1):
        canvas.setFillColor(white);canvas.rect(0,0,width,height,fill=1,stroke=0)
        for x,w,color in [(0,width*.76,'#0080C6'),(width*.76,width*.12,'#E42F44'),(width*.88,width*.12,'#EC8922')]:
            canvas.setFillColor(HexColor(color));canvas.rect(x,height-5,w,5,fill=1,stroke=0)
        canvas.drawImage(str(logo),28,height-63,width=88,height=36,preserveAspectRatio=True,anchor='c',mask='auto')
        canvas.setFillColor(HexColor(INK));canvas.setFont('Helvetica-Bold',18);canvas.drawString(132,height-40,'PALLET / ORDER DETAILS')
        text(f"ทะเบียน: {trip['truck_id']} | {trip['truck_type']}",28,height-85,width-56)
        for index,(kind,line) in enumerate(lines):
            if kind!='space':text(line,28 if kind=='header' else 44,height-120-index*17,width-(56 if kind=='header' else 88),size=11 if kind=='header' else 10,color=BLUE if kind=='header' else INK)
        canvas.setFont('Helvetica',7);canvas.setFillColor(HexColor(MUTED));canvas.drawString(28,21,f"TRIP {trip['id']}");canvas.drawRightString(width-28,21,f'PAGE {number} / {pages}')
        canvas.showPage()
    canvas.save()
