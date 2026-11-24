"""Write the consumer fonts, CSS, specimen and local download archive."""
from pathlib import Path
from hashlib import sha256
import json,shutil,tomllib
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from sources.validate import STYLES,validate_font

ROOT=Path(__file__).resolve().parents[1]
CSS='''@font-face {
  font-family: "Fractal Mono";
  src: url("./fonts/webfonts/FractalMono-Variable.woff2") format("woff2");
  font-style: normal;
  font-weight: 100 800;
  font-display: swap;
}
.fractal-mono {
  font-family: "Fractal Mono", ui-monospace, monospace;
  font-optical-sizing: none;
  font-variant-ligatures: no-discretionary-ligatures;
}
.fractal-mono-optical { font-optical-sizing: auto; }
.fractal-mono-ligatures { font-variant-ligatures: discretionary-ligatures; }
'''

def specimen():
 image=Image.new('RGB',(1600,1780),'#fafaf7');d=ImageDraw.Draw(image);label=ImageFont.load_default(size=25)
 d.text((60,40),'Fractal Mono',font=ImageFont.load_default(size=58),fill='#171815')
 for i,(weight,style) in enumerate(STYLES.items()):
  face=ImageFont.truetype(str(ROOT/'fonts/otf'/f'FractalMono-{style}.otf'),72);y=220+i*135
  d.text((60,y-55),style,font=label,fill='#55584a');d.text((290,y),'Fractal Mono 0123456789',font=face,fill='black',anchor='ls')
 face=ImageFont.truetype(str(ROOT/'fonts/otf/FractalMono-Regular.otf'),62)
 for i,line in enumerate(['ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz','R r O o 0 u J ! ? ( ) { } [ ]','$ € £ ¥ ¢ ₹ © ® ™ § ¶','+ − × ÷ = ≠ ≈ < > ≤ ≥ ± ∞']):d.text((60,1330+i*88),line,font=face,fill='black',anchor='ls')
 path=ROOT/'documentation/specimen.png';path.parent.mkdir(exist_ok=True);image.save(path)

def main():
 cfg=tomllib.loads((ROOT/'sources/config.toml').read_text());build=(ROOT/'sources'/cfg['outputDir']).resolve();files=[]
 for style in STYLES.values():
  source=build/'otf'/f'FractalMono-{style}.otf';validate_font(source);otf=ROOT/'fonts/otf'/source.name;otf.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,otf);files.append(otf)
  font=TTFont(source,recalcTimestamp=False);font.flavor='woff2';web=ROOT/'fonts/webfonts'/f'FractalMono-{style}.woff2';web.parent.mkdir(parents=True,exist_ok=True);font.save(web);font.close();files.append(web)
 variable=build/'variable/FractalMono[wght,opsz].ttf';validate_font(variable);target=ROOT/'fonts/variable/FractalMono-Variable.ttf';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(variable,target);files.append(target)
 web=ROOT/'fonts/webfonts/FractalMono-Variable.woff2';shutil.copy2(variable.with_suffix('.woff2'),web);files.append(web)
 (ROOT/'fractal-mono.css').write_text(CSS);specimen()
 sums={str(p.relative_to(ROOT/'fonts')):sha256(p.read_bytes()).hexdigest() for p in sorted(files)};(ROOT/'fonts/SHA256SUMS').write_text(''.join(f'{h}  {p}\n' for p,h in sums.items()))
 outputs=[*files,ROOT/'fonts/SHA256SUMS',ROOT/'fractal-mono.css',ROOT/'documentation/specimen.png',ROOT/'README.md',ROOT/'LICENSE.txt'];details={str(p.relative_to(ROOT)):{'sha256':sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(outputs)}
 manifest={'status':'local-unreleased','version':f"{cfg['versionMajor']}.{cfg['versionMinor']:03}",'otfFonts':8,'variableFonts':1,'webFonts':9,'files':details};manifest['sha256']=sha256(json.dumps(details,sort_keys=True).encode()).hexdigest();(ROOT/'build/package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 archive=ROOT/'dist'/f"FractalMono-{manifest['version']}.zip";archive.parent.mkdir(exist_ok=True)
 with ZipFile(archive,'w',compression=ZIP_DEFLATED,compresslevel=9) as out:
  for p in sorted(outputs):
   info=ZipInfo(str(p.relative_to(ROOT)),(1980,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o100644<<16;out.writestr(info,p.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
 print('Exported 8 OTFs, 1 variable TTF and 9 WOFF2s; archive:',archive.relative_to(ROOT))

if __name__=='__main__':main()
