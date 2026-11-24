"""Verify complete fresh-source coverage, features and variable exports."""
from pathlib import Path
import io,json,unittest,unicodedata
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'build/source';STEM='FractalMono'
CV={'cv01':6,'cv02':5,'cv03':7,'cv04':4,'cv05':6,'cv06':1,'cv07':10,'cv08':16,'cv09':1,'cv10':4,'cv11':15,'cv12':19,'cv14':5,'cv15':4,'cv16':1,'cv17':1,'cv18':15,'cv19':5,'cv20':5,'cv21':2,'cv22':1,'cv99':2};SS={'ss01':59,'ss02':38,'ss19':4,'ss20':2}

def shaped(path,text,features=None,weight=400,optical=14,language=None):
 font=hb.Font(hb.Face(path.read_bytes()));font.set_variations({'wght':weight,'opsz':optical});buffer=hb.Buffer();buffer.add_str(text);buffer.guess_segment_properties()
 if language:buffer.language=language
 hb.shape(font,buffer,features or {});return [font.glyph_to_string(g.codepoint) for g in buffer.glyph_infos],[(p.x_advance,p.x_offset,p.y_offset) for p in buffer.glyph_positions]

class CompleteRebuildTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=OUT/'variable'/f'{STEM}[wght,opsz].ttf';cls.font=TTFont(cls.path);cls.cmap=cls.font.getBestCmap();cls.contract=json.loads((ROOT/'sources/feature-contract.json').read_text())
 def test_complete_inventory(self):
  inventory=json.loads((ROOT/'sources/provenance.json').read_text())['glyphs'];self.assertEqual(set(self.font.getGlyphOrder()),{g['name'] for g in inventory});self.assertEqual(len(self.font.getGlyphOrder()),1755);self.assertEqual(len(self.cmap),1372);self.assertEqual(self.cmap[0x2001],self.cmap[0x2003])
 def test_all_feature_tags_and_substitution_counts(self):
  records=self.font['GSUB'].table.FeatureList.FeatureRecord;lookups=self.font['GSUB'].table.LookupList.Lookup;counts={}
  for r in records:
   if r.FeatureTag.startswith(('cv','ss')):counts[r.FeatureTag]=sum(len(getattr(st,'mapping',{})) for i in r.Feature.LookupListIndex for st in lookups[i].SubTable)
  self.assertEqual(counts,CV|SS);self.assertNotIn('liga',{r.FeatureTag for r in records});self.assertEqual(len(self.contract['dlig']),150)
 def test_default_ligatures_stay_off(self):
  for seq in self.contract['dlig']:
   names,positions=shaped(self.path,seq,{'dlig':False});self.assertEqual(len(names),len(seq),seq);self.assertEqual(sum(p[0] for p in positions),579*len(seq),seq)
 def test_all_discretionary_ligatures_keep_source_cells(self):
  for weight,optical in [(100,9),(400,14),(800,72)]:
   for seq,target in self.contract['dlig'].items():
    names,positions=shaped(self.path,seq,{'dlig':True},weight,optical);self.assertEqual(names,['SPC']*(len(seq)-1)+[target],(seq,weight,optical));self.assertEqual(sum(p[0] for p in positions),579*len(seq),seq)
 def test_literal_sequences_stay_literal(self):
  for seq in self.contract['literalSequences']:
   a=shaped(self.path,seq,{'dlig':False});b=shaped(self.path,seq,{'dlig':True});self.assertEqual(a,b,seq)
 def test_optional_dots_preserve_defaults(self):
  self.assertEqual(shaped(self.path,'Oo0')[0],['O','o','zero']);self.assertEqual(shaped(self.path,'Oo',{'cv21':True})[0],['O.dotted','o.dotted']);self.assertEqual(shaped(self.path,'0',{'cv22':True})[0],['zero.dotless']);self.assertEqual(shaped(self.path,'0',{'zero':True})[0],['zero.zero'])
 def test_stylistic_sets_and_combinations(self):
  self.assertEqual(shaped(self.path,'f',{'ss20':True})[0],['f.ss20']);self.assertEqual(shaped(self.path,'f',{'ss20':True,'cv09':True})[0],['f.cv09.ss20']);self.assertEqual(shaped(self.path,'!=',{'dlig':True,'ss19':True})[0],['SPC','exclam_equal.liga.ss19'])
  self.assertEqual(shaped(self.path,'$>',{'dlig':True,'cv14':True})[0],['SPC','dollar_greater.liga.cv14']);self.assertEqual(shaped(self.path,'&&',{'dlig':True,'cv15':True})[0],['SPC','ampersand_ampersand.liga.cv15'])
 def test_language_and_contextual_forms(self):
  self.assertEqual(shaped(self.path,'i',language='tr')[0],['i.loclTRK']);names,_=shaped(self.path,'A:B A;B STRAßE');self.assertTrue({'colon.case','semicolon.case','germandbls.calt'}<=set(names));self.assertEqual(shaped(self.path,'l·l',language='ca')[0],['l','periodcentered.loclCAT','l'])
  self.assertEqual(sum(p[0] for p in shaped(self.path,'l·l',language='ca')[1]),1158);self.assertEqual(shaped(self.path,'L·L',language='ca')[0],['L','periodcentered.loclCAT.case','L']);self.assertEqual(shaped(self.path,'i',language='az')[0],['i.loclTRK'])
 def test_fraction_parts_and_advance(self):
  self.assertEqual(shaped(self.path,'1',{'numr':True})[0],['one.numr']);self.assertEqual(shaped(self.path,'2',{'dnom':True})[0],['two.dnom']);names,positions=shaped(self.path,'1/2',{'frac':True});self.assertEqual(names,['one.numr','fraction','two.dnom']);self.assertEqual(sum(p[0] for p in positions),1737)
  self.assertEqual(shaped(self.path,'12/345',{'frac':True})[0],['one.numr','two.numr','fraction','three.dnom','four.dnom','five.dnom']);self.assertEqual(shaped(self.path,'2',{'sups':True})[0],['uni00B2']);self.assertEqual(shaped(self.path,'2',{'subs':True})[0],['uni2082']);self.assertEqual(shaped(self.path,'2',{'sinf':True})[0],['uni2082']);self.assertEqual(shaped(self.path,'2a 1o',{'ordn':True})[0],['two','ordfeminine','space','one','ordmasculine']);self.assertEqual(shaped(self.path,'ao',{'ordn':True})[0],['a','o'])
 def test_all_normalization_pairs(self):
  for cp in self.cmap:
   text=chr(cp);nfd=unicodedata.normalize('NFD',text)
   if text!=nfd:self.assertEqual(shaped(self.path,text),shaped(self.path,nfd),hex(cp))
 def test_source_provenance_covers_every_glyph(self):
  from sources.validate import validate_source
  self.assertEqual(validate_source()['glyphs'],1755)
 def test_static_variable_parity(self):
  for weight,style in [(100,'Thin'),(400,'Regular'),(800,'ExtraBold')]:
   instance=instantiateVariableFont(self.font,{'wght':weight,'opsz':14},inplace=False);buffer=io.BytesIO();instance.save(buffer);instance=TTFont(io.BytesIO(buffer.getvalue()));static=TTFont(OUT/'static'/f'{STEM}-{style}.ttf')
   self.assertEqual(instance['hmtx'].metrics,static['hmtx'].metrics)
   for name in instance.getGlyphOrder():self.assertEqual(instance['glyf'][name].getCoordinates(instance['glyf']),static['glyf'][name].getCoordinates(static['glyf']),(weight,name))
 def test_all_required_outlines_and_extreme_bounds(self):
  blank={'NULL','SPC',self.cmap[13],self.cmap[32],self.cmap[160],self.cmap[0x2001],self.cmap[0x200B],self.cmap[0xFEFF]}
  for weight,optical in [(100,9),(400,14),(800,72),(450,36)]:
   font=instantiateVariableFont(self.font,{'wght':weight,'opsz':optical},inplace=False)
   for name in font.getGlyphOrder():
    g=font['glyf'][name]
    if name not in blank:self.assertTrue(g.isComposite() or g.numberOfContours>0,(weight,optical,name))
    if g.numberOfContours:self.assertLessEqual(g.yMax,font['OS/2'].usWinAscent,name);self.assertGreaterEqual(g.yMin,-font['OS/2'].usWinDescent,name)
 def test_web_roundtrip(self):
  web=TTFont(OUT/'variable'/f'{STEM}[wght,opsz].woff2');self.assertEqual(web.getGlyphOrder(),self.font.getGlyphOrder());self.assertEqual(web.getBestCmap(),self.cmap)

if __name__=='__main__':unittest.main()
