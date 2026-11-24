"""Verify the shipped formats retain the complete font contract."""
from pathlib import Path
import unittest
import glyphsLib
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.areaPen import AreaPen

ROOT=Path(__file__).resolve().parents[2]
STYLES={100:'Thin',200:'ExtraLight',300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold',800:'ExtraBold'}

class DeliveryTests(unittest.TestCase):
 def test_delivery_has_only_the_requested_font_formats(self):
  expected={*(f'otf/FractalMono-{s}.otf' for s in STYLES.values()),*(f'webfonts/FractalMono-{s}.woff2' for s in STYLES.values()),'variable/FractalMono-Variable.ttf','webfonts/FractalMono-Variable.woff2','SHA256SUMS'}
  self.assertEqual({str(p.relative_to(ROOT/'fonts')) for p in (ROOT/'fonts').rglob('*') if p.is_file()},expected)
 def test_otf_features_metrics_and_web_roundtrip(self):
  for weight,style in STYLES.items():
   otf=TTFont(ROOT/'fonts/otf'/f'FractalMono-{style}.otf');ttf=TTFont(ROOT/'build/source/static'/f'FractalMono-{style}.ttf');master=TTFont(ROOT/'build/source/masters'/f'w{weight}-o14/master.ttf');web=TTFont(ROOT/'fonts/webfonts'/f'FractalMono-{style}.woff2')
   self.assertEqual(otf.sfntVersion,'OTTO');self.assertIn('CFF ',otf);self.assertNotIn('glyf',otf);self.assertEqual(otf.getBestCmap(),ttf.getBestCmap());self.assertEqual(otf['hmtx'].metrics,master['hmtx'].metrics)
   self.assertEqual({n:v[0] for n,v in otf['hmtx'].metrics.items()},{n:v[0] for n,v in ttf['hmtx'].metrics.items()})
   self.assertEqual(otf['name'].getDebugName(16),'Fractal Mono');self.assertEqual(otf['name'].getDebugName(17),style);self.assertEqual(bool(otf['head'].macStyle&1),style=='Bold');self.assertEqual(bool(otf['OS/2'].fsSelection&0x20),style=='Bold')
   for tag in ['GSUB','GPOS','GDEF']:self.assertEqual(otf[tag].compile(otf),ttf[tag].compile(ttf),(style,tag))
   for tag in ['CFF ','GSUB','GPOS','GDEF','hmtx','cmap']:self.assertEqual(otf.reader[tag],web.reader[tag],(style,tag,'web roundtrip'))
 def test_cff_outlines_match_the_editable_cubic_source(self):
  font=glyphsLib.load(ROOT/'sources/FractalMono.glyphspackage')
  for weight,style in STYLES.items():
   key='REGULAR-400-14' if weight==400 else f'W{weight}-O14';layers={g.name:g.layers[key] for g in font.glyphs};compiled=TTFont(ROOT/'fonts/otf'/f'FractalMono-{style}.otf').getGlyphSet()
   for name,layer in layers.items():
    a,b=BoundsPen(layers),BoundsPen(compiled);layer.draw(a);compiled[name].draw(b);self.assertEqual(a.bounds is None,b.bounds is None,(style,name))
    if a.bounds:
     for x,y in zip(a.bounds,b.bounds):self.assertAlmostEqual(x,y,delta=.005,msg=(style,name,'bounds'))
    a,b=AreaPen(layers),AreaPen(compiled);layer.draw(a);compiled[name].draw(b);self.assertAlmostEqual(a.value,b.value,delta=max(.1,abs(a.value)*1e-5),msg=(style,name,'area'))

if __name__=='__main__':unittest.main()
