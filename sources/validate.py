"""Validate the complete fresh source and its compiled exports."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,tomllib,unicodedata
import openstep_plist
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ufoLib.filenames import userNameToFileName

ROOT=Path(__file__).resolve().parents[1]
STYLES={100:'Thin',200:'ExtraLight',300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold',800:'ExtraBold'}

def require(condition,message):
 if not condition:raise ValueError(message)

def config():return tomllib.loads((ROOT/'sources/config.toml').read_text())

def validate_source():
 cfg=config();provenance=json.loads((ROOT/'sources/provenance.json').read_text());package=ROOT/'sources'/cfg['sources'][0];info=openstep_plist.loads((package/'fontinfo.plist').read_text(),use_numbers=True)
 require(info['familyName']==cfg['familyName'],'source family differs from config');masters=info['fontMaster'];ids={m['id'] for m in masters};locations={tuple(m['axesValues']) for m in masters};require(locations=={(w,o) for w in STYLES for o in (9,14,72)},'source master locations are incomplete');require(len(ids)==24,'source requires 24 unique masters')
 entries=provenance['glyphs'];counts=dict(Counter(g['status'] for g in entries));require(counts=={'authored':1755},'source has unresolved provenance');require(provenance['summary']=={'authored':1755,'inherited':0,'mixed':0,'unknown':0},'provenance summary differs from its records');require(len(entries)==cfg['expectedGlyphCount'],'canonical inventory count changed');found=set();encoded=set()
 for entry in entries:
  path=package/'glyphs'/userNameToFileName(entry['name'],suffix='.glyph');payload=path.read_bytes();require(sha256(payload).hexdigest()==entry['sourceSha256'],'unreviewed source change: '+entry['name']);glyph=openstep_plist.loads(payload.decode(),use_numbers=True);require(glyph['glyphname']==entry['name'],'source filename/name mismatch');layers=glyph['layers'];require({layer['layerId'] for layer in layers}==ids,'incomplete masters: '+entry['name']);require(len(layers)==24,'extra layers: '+entry['name']);signature=None
  for layer in layers:
   require(layer['width'] in (0,579),'invalid cell width: '+entry['name']);shape=[]
   for contour in layer.get('shapes',[]):
    if 'ref' in contour:shape.append(('component',contour['ref']))
    else:shape.append(('path',contour.get('closed',True),[n[2].removesuffix('s') for n in contour['nodes']]))
   if signature is None:signature=shape
   require(signature==shape,'incompatible master structure: '+entry['name'])
  values=glyph.get('unicode',[]);values=values if isinstance(values,list) else [values];codes={u if isinstance(u,int) else int(u,16) for u in values};require(codes=={int(u[2:],16) for u in entry['unicodes']},'source Unicode differs from inventory: '+entry['name']);encoded|=codes;found.add(entry['name'])
 require(len(list((package/'glyphs').glob('*.glyph')))==len(found),'unlisted source glyph file');require(len(encoded)==cfg['expectedEncodedCharacters'],'encoded source count changed');return {'glyphs':len(found),'encodedCharacters':len(encoded),'masters':24,'provenance':provenance['summary']}

def validate_font(path):
 cfg=config();inventory=json.loads((ROOT/'sources/provenance.json').read_text())['glyphs'];required={int(u[2:],16) for g in inventory for u in g['unicodes']};names={g['name'] for g in inventory}
 with TTFont(path) as font:
  require(set(font.getGlyphOrder())==names,'compiled glyph inventory differs');cmap=font.getBestCmap();require(set(cmap)==required,'compiled Unicode coverage differs');require(cmap[0x2001]==cmap[0x2003],'canonical spaces differ');family=font['name'].getDebugName(16) or font['name'].getDebugName(1);require(family==cfg['familyName'],'compiled family name differs');require(font['post'].isFixedPitch==1,'fixed-pitch metadata is missing');require(all(width in (0,579) for width,lsb in font['hmtx'].metrics.values()),'compiled advance breaks the cell grid')
  for cp,name in cmap.items():require(font['hmtx'][name][0]==(0 if unicodedata.combining(chr(cp)) or cp in (13,0x200B,0xFEFF) else 579),'encoded advance differs: '+hex(cp))
  blank={'NULL','SPC',*(cmap[cp] for cp in (13,32,160,0x2001,0x200B,0xFEFF))}
  glyphs=font.getGlyphSet()
  for name in font.getGlyphOrder():
   pen=BoundsPen(glyphs);glyphs[name].draw(pen)
   if name not in blank:require(pen.bounds is not None,'empty required outline: '+name)
   if pen.bounds:require(pen.bounds[3]<=font['OS/2'].usWinAscent and pen.bounds[1]>=-font['OS/2'].usWinDescent,'clipped outline: '+name)
  tags={r.FeatureTag for r in font['GSUB'].table.FeatureList.FeatureRecord};require('liga' not in tags and 'dlig' in tags,'programming ligatures must stay opt-in');require({'sups','subs','sinf','ordn','frac','numr','dnom','zero','calt','locl','ccmp'}<=tags,'retained features are missing')
  if 'fvar' in font:
   require([(a.axisTag,a.minValue,a.defaultValue,a.maxValue) for a in font['fvar'].axes]==[('wght',100,400,800),('opsz',9,14,72)],'public axes differ');require(len(font['fvar'].instances)==8,'named weights are incomplete');require('avar' not in font,'unexpected axis remapping')
  return {'file':Path(path).name,'glyphs':len(names),'encodedCharacters':len(cmap),'sha256':sha256(Path(path).read_bytes()).hexdigest()}

def main():
 cfg=config();output=(ROOT/'sources'/cfg['outputDir']).resolve();source=validate_source();paths=[output/'variable'/'FractalMono[wght,opsz].ttf',*(output/'static'/f'FractalMono-{style}.ttf' for style in STYLES.values()),*(output/'otf'/f'FractalMono-{style}.otf' for style in STYLES.values())];reports=[validate_font(path) for path in paths];report={'source':source,'fonts':reports,'fontCount':len(reports)};(output/'validation-report.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Validated {len(reports)} fonts: {source["glyphs"]} glyphs, {source["encodedCharacters"]} codepoints, 24 fresh masters')

if __name__=='__main__':main()
