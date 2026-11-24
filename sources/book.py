"""Create the family book from the current compiled fresh fonts only."""
from pathlib import Path
from hashlib import sha256
import json,time
from PIL import Image,ImageDraw,ImageFont,features
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from sources.validate import STYLES,validate_font

ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'build/source';OUT=ROOT/'build/review'

def label(size):return ImageFont.load_default(size=size)

def page(title):
 image=Image.new('RGB',(2000,2600),'#fafaf7');draw=ImageDraw.Draw(image);draw.text((70,55),title,font=label(48),fill='#171815');return image,draw

def main():
 if not features.check('raqm'):raise RuntimeError('Pillow requires RAQM for feature proofs')
 OUT.mkdir(parents=True,exist_ok=True);pages=[];files=[];variable=BUILD/'variable/FractalMono[wght,opsz].ttf';validate_font(variable)
 for weight,style in STYLES.items():
  path=BUILD/'otf'/f'FractalMono-{style}.otf';files.append(path);image,d=page('Fractal Mono - '+style);face=ImageFont.truetype(str(path),76)
  lines=['Fractal Mono O o 0 r u J R ! ? {}','ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz','0123456789  0O1Il  minimum illinois','ÀÁÂÃÄÅ Æ Ð Đ Ħ Ł Ŋ Ø Œ Þ ẞ','àáâãäå æ ð đ ħ ł ŋ ø œ þ ß','Tiếng Việt: Ắ Ằ Ặ Ấ Ầ Ậ Ế Ệ','Ελληνικά αβγδεζηθικλμνξοπρστυφχψω','Привет мир  Українська мова','$ € £ ¥ ¢ ₹ © ® ™ § ¶']
  for i,text in enumerate(lines):d.text((70,250+i*140),text,font=face,fill='black',anchor='ls')
  d.text((70,1650),'Optional programming ligatures (dlig)',font=label(30),fill='#55584a');d.text((70,1800),'!= !== == === -> --> <-> => <=> <= >=',font=face,fill='black',anchor='ls',features=['dlig'])
  d.text((70,1920),'Default / optional dots',font=label(30),fill='#55584a');d.text((70,2050),'Oo0',font=face,fill='black',anchor='ls');d.text((500,2050),'Oo0',font=face,fill='black',anchor='ls',features=['cv21','cv22'])
  for i,optical in enumerate((9,14,72)):
   opticalface=ImageFont.truetype(str(variable),42);opticalface.set_variation_by_axes([weight,optical]);d.text((70,2200+i*110),f'opsz {optical}',font=label(25),fill='#55584a');d.text((280,2230+i*110),'Fractal Mono r u a f J 0O1Il',font=opticalface,fill='black',anchor='ls')
  image.save(OUT/f'weight-{weight}.png');pages.append(image)
 regular=BUILD/'otf/FractalMono-Regular.otf';font=TTFont(regular);cmap=font.getBestCmap();face=ImageFont.truetype(str(regular),84);chars=sorted(cmap)
 for sheet,start in enumerate(range(0,len(chars),80)):
  image,d=page(f'Fractal Mono - encoded repertoire {sheet+1}')
  for i,cp in enumerate(chars[start:start+80]):
   x=(i%8)*250;y=170+(i//8)*235;d.rectangle((x,y,x+249,y+234),outline='#d8d8ce');d.text((x+12,y+10),f'U+{cp:04X}',font=label(19),fill='#55584a');text=chr(cp)
   import unicodedata
   if unicodedata.combining(text):text='B'+text
   d.text((x+55,y+155),text,font=face,fill='black',anchor='ls')
  image.save(OUT/f'repertoire-{sheet+1:02}.png');pages.append(image)
 inventory=json.loads((ROOT/'sources/provenance.json').read_text())['glyphs'];entries=[g['name'] for g in inventory if not g['unicodes'] and g['name']!='.notdef'];mapping={0xF000+i:name for i,name in enumerate(entries)};mapping[0xF300]='SPC'
 for table in font['cmap'].tables:
  if table.isUnicode():table.cmap.update(mapping)
 proof=OUT/'unencoded-proof.otf';font.save(proof);face=ImageFont.truetype(str(proof),105)
 try:
  for sheet,start in enumerate(range(0,len(entries),50)):
   image,d=page(f'Fractal Mono - optional glyphs {sheet+1}')
   for i,name in enumerate(entries[start:start+50]):
    x=(i%5)*400;y=170+(i//5)*235;d.rectangle((x,y,x+399,y+234),outline='#d8d8ce');d.text((x+12,y+10),name[:38],font=label(16),fill='#55584a');text=chr(0xF000+start+i);origin=x+25
    if '.liga' in name:text=chr(0xF300)*(len(name.split('.liga')[0].split('_'))-1)+text
    glyphs=font.getGlyphSet();pen=BoundsPen(glyphs);glyphs[name].draw(pen)
    if font['hmtx'][name][0]==0 and pen.bounds:origin=x+200-(pen.bounds[0]+pen.bounds[2])/2*.105
    d.text((origin,y+170),text,font=face,fill='black',anchor='ls')
   image.save(OUT/f'optional-{sheet+1:02}.png');pages.append(image)
 finally:proof.unlink(missing_ok=True)
 pages[0].save(OUT/'fontbook.pdf',save_all=True,append_images=pages[1:],resolution=220,creationDate=time.gmtime(0),modDate=time.gmtime(0))
 manifest={'pages':len(pages),'family':'Fractal Mono','glyphs':1755,'encodedCharacters':len(chars),'fontInputs':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in [variable,*files]},'referenceFontInputs':[],'appearanceAcceptance':'pending'};(OUT/'fontbook-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(f'Wrote {len(pages)} pages: {OUT/"fontbook.pdf"}')

if __name__=='__main__':main()
