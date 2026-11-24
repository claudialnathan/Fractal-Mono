"""Check complete production interpolation and restricted input independence."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,unittest
import openstep_plist
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image,ImageDraw,ImageFont
import numpy as np
from sources.validate import validate_source
from sources.build import recording
from fontTools.pens.basePen import BasePen

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'build/source';VARIABLE=OUT/'variable/FractalMono[wght,opsz].ttf'

class ArmPen(BasePen):
 def __init__(self,glyphset):super().__init__(glyphset);self.contours=[];self.current=[]
 def _moveTo(self,p):self.current=[('M',p)]
 def _lineTo(self,p):self.current.append(('L',p))
 def _qCurveToOne(self,c,p):self.current.append(('Q',(self._getCurrentPoint(),c,p)))
 def _closePath(self):self.contours.append(self.current)

def arm_widths(font):
 gs=font.getGlyphSet();pen=ArmPen(gs);gs['R'].draw(pen);groups=[];group=[];base=[]
 for op,p in pen.contours[2]:
  if op=='Q':group.append(np.asarray(p))
  else:
   if group:groups.append(group);group=[]
   if op=='L' and abs(p[1])<.001:base.append(p[0])
 if group:groups.append(group)
 if len(groups)!=2 or len(base)!=2:raise ValueError('Unexpected R arm structure')
 outer,back=groups;inner=[c[::-1] for c in back[::-1]];points=[]
 for a,b,c in inner:
  for t in np.linspace(0,1,25):points.append((1-t)**2*a+2*(1-t)*t*b+t*t*c)
 points.append(np.array([min(base),0]));points=np.asarray(points);start=points[:-1];vectors=np.diff(points,axis=0);widths=[]
 def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
 for a,b,c in outer:
  for t in (.25,.5,.75):
   p=(1-t)**2*a+2*(1-t)*t*b+t*t*c;v=2*((1-t)*(b-a)+t*(c-b));length=np.linalg.norm(v)
   if length<1e-6:continue
   normal=np.array([v[1],-v[0]])/length;delta=start-p;den=cross(normal,vectors);valid=np.abs(den)>1e-8;distance=np.full_like(den,np.inf);fraction=np.full_like(den,-1);distance[valid]=cross(delta[valid],vectors[valid])/den[valid];fraction[valid]=cross(delta[valid],normal)/den[valid];valid &= (distance>0)&(fraction>=-1e-6)&(fraction<=1+1e-6)
   if valid.any():widths.append(float(distance[valid].min()))
   else:raise ValueError('R arm lacks an opposing edge')
 return max(base)-min(base),widths

class ProductionTests(unittest.TestCase):
 def test_symbol_wrappers_share_fractal_o(self):
  for weight in range(100,801,100):
   for optical in (9,14,72):
    font=TTFont(OUT/'masters'/f'w{weight}-o{optical}/master.ttf');glyf=font['glyf'];o,ends,flags=glyf['O'].getCoordinates(glyf);length=ends[0]+1
    for name in ['copyright','registered','circleplus','uni2299']:
     p,e,f=glyf[name].getCoordinates(glyf);self.assertEqual(list(p[:length]),list(o[:length]),(weight,optical,name));self.assertEqual(e[0],ends[0])
 def test_symbol_strokes_match_the_dollar(self):
  def width(font,name,y):
   pen=ArmPen(font.getGlyphSet());font.getGlyphSet()[name].draw(pen);points=[]
   for op,p in pen.contours[1 if name=='plus' else 0]:
    if op in ('M','L'):points.append(p)
    else:
     a,b,c=np.asarray(p)
     for t in np.linspace(0,1,25)[1:]:points.append((1-t)**2*a+2*(1-t)*t*b+t*t*c)
   hits=[]
   for a,b in zip(points,points[1:]+points[:1]):
    if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):hits.append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
   self.assertEqual(len(hits),2,(name,y,hits));return max(hits)-min(hits)
  for weight in range(100,801,100):
   for optical in (9,14,72):
    font=TTFont(OUT/'masters'/f'w{weight}-o{optical}/master.ttf');target=width(font,'dollar',730)
    for name,y in [('question',489),('braceleft',530),('parenleft',329),('bracketleft',200),('plus',450)]:self.assertAlmostEqual(width(font,name,y),target,delta=1.5,msg=(weight,optical,name))
 def test_capital_r_shares_its_bowl_and_accented_bases(self):
  for weight in range(100,801,100):
   for optical in (9,14,72):
    font=TTFont(OUT/'masters'/f'w{weight}-o{optical}/master.ttf');glyf=font['glyf'];p,pe,pf=glyf['P'].getCoordinates(glyf);r,re,rf=glyf['R'].getCoordinates(glyf)
    self.assertEqual(list(r[:len(p)]),list(p),(weight,optical));self.assertEqual(list(re[:len(pe)]),list(pe));self.assertEqual(list(rf[:len(pf)]),list(pf))
    for cp in (0x154,0x156,0x158):
     a,ae,af=glyf[font.getBestCmap()[cp]].getCoordinates(glyf);self.assertEqual(list(a[:len(r)]),list(r),(weight,optical,hex(cp)));self.assertEqual(list(ae[:len(re)]),list(re))
 def test_capital_r_turn_keeps_its_stroke(self):
  root=ROOT/'sources/FractalMono.glyphspackage/glyphs';r=openstep_plist.loads((root/'R_.glyph').read_text(),use_numbers=True);p=openstep_plist.loads((root/'P_.glyph').read_text(),use_numbers=True);p_layers={l['layerId']:l for l in p['layers']}
  def value(c,t):a,b,c,d=np.asarray(c);return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
  def tangent(c,t):a,b,c,d=np.asarray(c);return 3*((1-t)**2*(b-a)+2*(1-t)*t*(c-b)+t*t*(d-c))
  for layer in r['layers']:
   path=layer['shapes'][2]['nodes'];self.assertAlmostEqual(path[0][1]-path[-1][1],p_layers[layer['layerId']]['shapes'][0]['nodes'][8][0]-p_layers[layer['layerId']]['shapes'][0]['nodes'][0][0],delta=.01);row={'paths':[[[x,y,{'l':'line','c':'curve','o':'offcurve'}[kind[0]],kind.endswith('s')] for x,y,kind in path]]};curves=[];current=None
   for op,points in recording(row):
    if op=='curveTo':curves.append(np.array([current,*points]));current=points[-1]
    elif op in ('moveTo','lineTo'):current=points[-1]
   half=len(curves)//2;outer=curves[:half];inner=[c[::-1] for c in curves[half:][::-1]];base=p_layers[layer['layerId']]['shapes'];vertical=base[0]['nodes'][8][0]-base[0]['nodes'][0][0];horizontal=base[1]['nodes'][0][1]-base[0]['nodes'][7][1]
   for a,b in zip(outer,inner):
    for t in np.linspace(0,1,41):
     v=(tangent(a,t)+tangent(b,t))/2;n=np.array([-v[1],v[0]])/np.linalg.norm(v);width=float((value(a,t)-value(b,t))@n);expected=vertical;self.assertAlmostEqual(width,expected,delta=.6,msg=(layer['layerId'],t,width,expected))
 def test_reviewed_source_hashes(self):self.assertEqual(validate_source()['provenance'],{'authored':1755,'inherited':0,'mixed':0,'unknown':0})
 def test_manifest_only_declares_fresh_inputs(self):
  manifest=json.loads((OUT/'input-manifest.json').read_text());allowed={'sources/build.py','sources/config.toml','sources/provenance.json','sources/features.fea'}
  for rel,digest in manifest['inputs'].items():
   self.assertTrue(rel in allowed or rel.startswith('sources/FractalMono.glyphspackage/'),rel);self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest,rel)
 def test_intermediate_variations_preserve_cells_and_bounds(self):
  variable=TTFont(VARIABLE)
  for weight in range(100,801,25):
   for optical in (9,14,24,36,72):
    font=instantiateVariableFont(variable,{'wght':weight,'opsz':optical},inplace=False)
    expected,widths=arm_widths(font);self.assertLessEqual(max(abs(v-expected) for v in widths),1.5,(weight,optical,min(widths),max(widths),expected))
    for name,(advance,lsb) in font['hmtx'].metrics.items():self.assertIn(advance,(0,579),(weight,optical,name))
    for name in ['H','O','o','r','R','f','u','J','zero','g.cv03','m.cv06','hyphen_greater.liga']:
     glyph=font['glyf'][name];self.assertTrue(glyph.isComposite() or glyph.numberOfContours>0,(weight,optical,name));self.assertLessEqual(glyph.yMax,font['OS/2'].usWinAscent);self.assertGreaterEqual(glyph.yMin,-font['OS/2'].usWinDescent)
 def test_landmark_ink_and_default_dots(self):
  face=ImageFont.truetype(str(VARIABLE),180)
  for weight in range(100,801,100):
   for optical in (9,14,72):
    face.set_variation_by_axes([weight,optical])
    for text in ['H','O','o','r','f','u','J','0']:
     image=Image.new('L',(180,260),255);ImageDraw.Draw(image).text((30,190),text,font=face,fill=0,anchor='ls');self.assertGreater(np.sum(np.asarray(image)<128),50,(weight,optical,text))
 def test_intermediate_polygon_strokes_do_not_collapse(self):
  def areas(font):
   result={};glyf=font['glyf']
   for name in font.getGlyphOrder():
    coordinates,ends,flags=glyf[name].getCoordinates(glyf);start=0
    for index,end in enumerate(ends):
     points=list(coordinates[start:end+1]);on_curve=all(flags[i]&1 for i in range(start,end+1));start=end+1
     if len(points)==4 and on_curve:result[name,index]=abs(sum(x*v-u*y for (x,y),(u,v) in zip(points,points[1:]+points[:1]))/2)
   return result
  variable=TTFont(VARIABLE)
  for optical in (9,14,72):
   masters={w:areas(TTFont(OUT/'masters'/f'w{w}-o{optical}/master.ttf')) for w in range(100,801,100)}
   for weight in range(150,751,100):
    middle=areas(instantiateVariableFont(variable,{'wght':weight,'opsz':optical},inplace=False))
    for key,value in middle.items():
     if key in masters[weight-50] and key in masters[weight+50]:self.assertGreaterEqual(value+1,min(masters[weight-50][key],masters[weight+50][key])*.95,(weight,optical,key))
 def test_intermediate_repertoire_has_visible_ink(self):
  face=ImageFont.truetype(str(VARIABLE),100);characters=set(TTFont(VARIABLE).getBestCmap())-{13,32,160,0x2001,0x2003,0x200B,0xFEFF}
  for weight in range(150,751,100):
   for optical in (9,14,72):
    face.set_variation_by_axes([weight,optical])
    for cp in characters:self.assertIsNotNone(face.getmask(chr(cp)).getbbox(),(weight,optical,hex(cp)))
 @unittest.skipUnless(sys.platform=='darwin','macOS sandbox-exec input-denial check')
 def test_two_restricted_builds_match(self):
  manifest=json.loads((OUT/'input-manifest.json').read_text())
  with tempfile.TemporaryDirectory(prefix='fractal-full-isolation-') as directory:
   clean=Path(directory)
   for rel in manifest['inputs']:
    target=clean/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,target)
   runtime=Path(sys.executable).parent.parent;denied=[Path.home()/'repos/CLN',Path.home()/'Documents/Font Backups',Path.home()/'Library/Fonts']
   profile='(version 1) (allow default) (deny network*)\n(deny file-read-data '+' '.join(f'(subpath {json.dumps(str(p))})' for p in denied)+f' (require-all (subpath {json.dumps(str(ROOT))}) (require-not (subpath {json.dumps(str(runtime))}))))\n'
   reference=Path.home()/'Documents/Font Backups/FractalMono-approved-pre-sweep-2026-08-26-recovered-2026-09-11-101003-AWST/fonts/desktop/FractalMono-Variable.ttf';protected=[ROOT/'working/source-history.zip',reference];forbidden=[ROOT/'sources/FractalMono.glyphspackage/fontinfo.plist',*[p for p in protected if p.is_file()]]
   probe='from pathlib import Path\n'
   for path in forbidden:probe+=f'try:\n Path({str(path)!r}).read_bytes()\nexcept PermissionError:\n pass\nelse:\n raise RuntimeError("forbidden input was readable")\n'
   command=['sandbox-exec','-p',profile,sys.executable];result=subprocess.run(command+['-c',probe],cwd=clean,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
   for attempt in range(2):
    result=subprocess.run(command+['-m','sources.build'],cwd=clean,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
    for relative,digest in manifest['outputs'].items():self.assertEqual(hashlib.sha256((clean/'build/source'/relative).read_bytes()).hexdigest(),digest,(attempt,relative))

if __name__=='__main__':unittest.main()
