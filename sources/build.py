"""Compile the fresh editable Fractal source into static and variable fonts."""
from __future__ import annotations
from pathlib import Path
import hashlib,json,tomllib,math
import importlib.metadata,platform
from copy import deepcopy
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuMultiPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.ttLib import TTFont,newTable
from fontTools.ttLib.tables.O_S_2f_2 import Panose
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.feaLib.builder import addOpenTypeFeatures
from fontTools.designspaceLib import DesignSpaceDocument,AxisDescriptor,SourceDescriptor,InstanceDescriptor
from fontTools.varLib import build as build_variable
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.otlLib.builder import buildStatTable
import glyphsLib
from glyphsLib.classes import GSLayer,GSPath,GSNode

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/source'
STYLES={100:'Thin',200:'ExtraLight',300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold',800:'ExtraBold'}
FAMILY='Fractal Mono'
STEM='FractalMono'
FEATURES=ROOT/'sources/features.fea'
TIMESTAMP=2082844800
DELIVERY={}

def precise_grid_variations(variable,fonts,locations,names):
 fonts=[TTFont(path,recalcTimestamp=False) for path in fonts]
 def weight(w):return (w-400)/(300 if w<400 else 400)
 def support(w,o):
  result={}
  if w!=400:result['wght']=(weight(max(100,w-100)),weight(w),weight(min(800,w+100)))
  if o!=14:result['opsz']=(-1,-1,0) if o==9 else (0,1,1)
  return result
 for name in names:
  coords={loc:f['glyf']._getCoordinatesAndControls(name,f['hmtx'].metrics)[0] for loc,f in zip(locations,fonts)};base=coords[400,14];variations=[]
  controls=variable['glyf']._getCoordinatesAndControls(name,variable['hmtx'].metrics)[1]
  for w,o in locations:
   if (w,o)==(400,14):continue
   delta=coords[w,o]-base if w==400 or o==14 else coords[w,o]-coords[w,14]-coords[400,o]+base
   if any(x or y for x,y in delta):
    variation=TupleVariation(support(w,o),delta);variation.optimize(base,controls.endPts,tolerance=0);variations.append(variation)
  variable['gvar'].variations[name]=variations
 for font in fonts:font.close()

def recording(row):
 layer=GSLayer()
 for contour in row['paths']:
  path=GSPath();path.closed=True
  for x,y,kind,smooth in contour:path.nodes.append(GSNode((x,y),kind,smooth=smooth))
  layer.paths.append(path)
 pen=RecordingPen();layer.drawPoints(PointToSegmentPen(pen,outputImpliedClosingLine=True));return pen.value

def quadratics(masters):
 names=[r['name'] for r in masters[0]]
 if any([r['name'] for r in master]!=names for master in masters):raise ValueError('Master glyph order mismatch')
 result=[{} for master in masters]
 deferred=[]
 for index,name in enumerate(names):
  if masters[0][index].get('components'):
   deferred.append(index);continue
  records=[recording(master[index]) for master in masters]
  structure=[(op,len(points)) for op,points in records[0]]
  if any([(op,len(points)) for op,points in record]!=structure for record in records):raise ValueError('Incompatible fresh drawing: '+name)
  pens=[TTGlyphPen(None) for master in masters];multi=Cu2QuMultiPen(pens,max_err=.3)
  for i,(op,count) in enumerate(structure):
   if op in ('closePath','endPath'):getattr(multi,op)()
   else:getattr(multi,op)([record[i][1] for record in records])
  for glyphs,pen in zip(result,pens):
   g=pen.glyph();g.recalcBounds(None);glyphs[name]=g
 for index in deferred:
  name=names[index];structure=[c['name'] for c in masters[0][index]['components']]
  for master,glyphs in zip(masters,result):
   require=[c['name'] for c in master[index]['components']]
   if require!=structure:raise ValueError('Incompatible component references: '+name)
   pen=TTGlyphPen(glyphs)
   for component in master[index]['components']:
    if component['name'] not in glyphs:raise ValueError('Unresolved fresh component: '+component['name'])
    pen.addComponent(component['name'],tuple(component['transform']))
   glyph=pen.glyph(componentFlags=0x1000);glyph.recalcBounds(glyphs);glyphs[name]=glyph
 return result

def static(rows,glyphs,path,weight=400,optical=14,features=True,win_ascent=None,win_descent=None):
 family=FAMILY;style=STYLES[weight]
 cmap={int(u,16):r['name'] for r in rows for u in r.get('unicodes',[r['unicode']] if r['unicode'] else [])}
 metrics={r['name']:(r['width'],getattr(glyphs[r['name']],'xMin',0)) for r in rows}
 fb=FontBuilder(1000,isTTF=True);fb.setupGlyphOrder([r['name'] for r in rows]);fb.setupCharacterMap(cmap);fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics);fb.setupHorizontalHeader(ascent=900,descent=-250,lineGap=0)
 names={'familyName':family,'styleName':style,'typographicFamily':family,'typographicSubfamily':style,'uniqueFontIdentifier':f'{STEM}-{style}-o{optical}','fullName':family+' '+style,'psName':STEM+'-'+style,'version':'Version 1.000','designer':'Claudia Nathan','description':'Fresh-source repertoire proof.'}
 if DELIVERY:
  names.update({'version':f"Version {DELIVERY['versionMajor']}.{DELIVERY['versionMinor']:03}",'manufacturer':DELIVERY['manufacturer'],'designer':DELIVERY['designer'],'description':DELIVERY['description'].format(familyName=family),'copyright':DELIVERY['copyright'].format(familyName=family),'licenseDescription':'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org','licenseInfoURL':'https://openfontlicense.org'})
 fb.setupNameTable(names,mac=False)
 panose=Panose();panose.bFamilyType=2;panose.bSerifStyle=11;panose.bWeight=2+weight//100;panose.bProportion=9
 fb.setupOS2(version=4,sTypoAscender=900,sTypoDescender=-250,sTypoLineGap=0,usWinAscent=win_ascent or max(900,max(getattr(g,'yMax',0) for g in glyphs.values())),usWinDescent=win_descent or max(250,-min(getattr(g,'yMin',0) for g in glyphs.values())),sxHeight=528,sCapHeight=680,usWeightClass=weight,usWidthClass=5,fsSelection=0x80|(0x20 if weight>=700 else 0x40),achVendID=DELIVERY.get('vendorID','CLNN'),panose=panose,ulCodePageRange1=1,ulCodePageRange2=0)
 fb.font['head'].macStyle=1 if weight>=700 else 0
 fb.setupPost(isFixedPitch=1);fb.setupMaxp()
 prep=newTable('prep');prep.program=Program();prep.program.fromBytecode([0xB8,0x01,0xFF,0x85,0xB0,0x04,0x8D]);fb.font['prep']=prep
 gasp=newTable('gasp');gasp.gaspRange={65535:15};fb.font['gasp']=gasp
 if features:addOpenTypeFeatures(fb.font,FEATURES)
 fb.font['head'].created=TIMESTAMP;fb.font['head'].modified=TIMESTAMP;fb.font.recalcTimestamp=False;path.parent.mkdir(parents=True,exist_ok=True);fb.save(path)
 return fb.font

def static_otf(rows,master,path,win_ascent=None,win_descent=None):
 class Drawing:
  def __init__(self,row):self.row=row
  def draw(self,pen):
   for op,points in recording(self.row):getattr(pen,op)(*points)
   for component in self.row.get('components',[]):pen.addComponent(component['name'],tuple(component['transform']))
 drawings={row['name']:Drawing(row) for row in rows};charstrings={}
 for row in rows:
  pen=T2CharStringPen(row['width'],drawings,roundTolerance=0);drawings[row['name']].draw(pen);charstrings[row['name']]=pen.getCharString()
 fb=FontBuilder(1000,isTTF=False);fb.setupGlyphOrder(master.getGlyphOrder());fb.setupCharacterMap(master.getBestCmap());fb.setupHorizontalMetrics(master['hmtx'].metrics)
 for tag in ['head','hhea','OS/2','name']:fb.font[tag]=deepcopy(master[tag])
 if win_ascent:fb.font['OS/2'].usWinAscent=max(win_ascent,master['OS/2'].usWinAscent)
 if win_descent:fb.font['OS/2'].usWinDescent=max(win_descent,master['OS/2'].usWinDescent)
 style=master['name'].getDebugName(17);bold=style=='Bold';legacy_family=FAMILY if style in ('Regular','Bold') else FAMILY+' '+style
 for platform,encoding,language in [(3,1,0x409)]:
  fb.font['name'].setName(legacy_family,1,platform,encoding,language);fb.font['name'].setName('Bold' if bold else 'Regular',2,platform,encoding,language)
 fb.font['OS/2'].fsSelection=0x80|(0x20 if bold else 0x40);fb.font['head'].macStyle=1 if bold else 0
 name=master['name'].getDebugName(6);info={'FullName':master['name'].getDebugName(4),'FamilyName':FAMILY,'Weight':master['name'].getDebugName(2),'version':f"{DELIVERY['versionMajor']}.{DELIVERY['versionMinor']:03}",'Copyright':master['name'].getDebugName(0),'isFixedPitch':True}
 fb.setupCFF(name,info,charstrings,{});fb.setupPost(isFixedPitch=1);fb.setupMaxp();addOpenTypeFeatures(fb.font,FEATURES);fb.font.recalcTimestamp=False;path.parent.mkdir(parents=True,exist_ok=True);fb.save(path)
 return fb.font

def family():
 production=True;coverage_stage='full'
 locations=[(w,o) for o in (14,9,72) for w in range(100,801,100)]
 source_path=ROOT/'sources'/DELIVERY['sources'][0];font=glyphsLib.load(source_path)
 if len(font.masters)!=24:raise ValueError('The fresh source does not yet contain all 24 masters')
 inventory=json.loads((ROOT/'sources/provenance.json').read_text())['glyphs'];required={int(u[2:],16) for g in inventory for u in g['unicodes']}
 selected=[g for g in font.glyphs if coverage_stage=='full' or g.name=='.notdef' or any(int(u,16) in required for u in g.unicodes)]
 if {int(u,16) for g in selected for u in g.unicodes}!=required:raise ValueError('Requested stage coverage is missing')
 if production:
  inventory=json.loads((ROOT/'sources/provenance.json').read_text())['glyphs']
  if {g.name for g in selected}!={g['name'] for g in inventory}:raise ValueError('Fresh source differs from the canonical inventory')
  if len(selected)!=DELIVERY['expectedGlyphCount']:raise ValueError('Fresh source glyph count is incomplete')
  if len(required)!=DELIVERY['expectedEncodedCharacters']:raise ValueError('Fresh encoded coverage is incomplete')
 masters=[]
 for w,o in locations:
  master='REGULAR-400-14' if (w,o)==(400,14) else f'W{w}-O{o}'
  rows=[]
  layers={g.name:g.layers[master] for g in font.glyphs}
  for g in selected:
   layer=g.layers[master]
   if layer is None:raise ValueError('Fresh master is missing: '+g.name)
   components=[]
   if layer.components and not layer.paths:
    components=[{'name':c.name,'transform':list(c.transform)} for c in layer.components]
   elif layer.components:
    decomposed=DecomposingRecordingPen(layers);layer.draw(decomposed);fresh=GSLayer();fresh.width=layer.width;decomposed.replay(fresh.getPen());layer=fresh
   rows.append({'name':g.name,'unicode':g.unicode,'unicodes':list(g.unicodes),'width':layer.width,'components':components,'paths':[[[float(n.position.x),float(n.position.y),n.type,n.smooth] for n in p.nodes] for p in layer.paths]})
  masters.append(rows)
 compiled=quadratics(masters);ds=DesignSpaceDocument();cubic_bounds=[]
 for master in font.masters:
  if master.axes[1]!=14:continue
  layers={g.name:g.layers[master.id] for g in selected}
  for layer in layers.values():
   pen=BoundsPen(layers);layer.draw(pen)
   if pen.bounds:cubic_bounds.append(pen.bounds)
 # Cubic extrema can exceed rounded TrueType bounds.
 cff_ascent=max(900,math.ceil(max(b[3] for b in cubic_bounds)));cff_descent=max(250,math.ceil(-min(b[1] for b in cubic_bounds)))
 win_ascent=max(900,max(getattr(g,'yMax',0) for master in compiled for g in master.values()));win_descent=max(250,-min(getattr(g,'yMin',0) for master in compiled for g in master.values()))
 for tag,name,minimum,default,maximum in [('wght','Weight',100,400,800),('opsz','Optical Size',9,14,72)]:
  axis=AxisDescriptor();axis.tag=tag;axis.name=name;axis.minimum=minimum;axis.default=default;axis.maximum=maximum;ds.addAxis(axis)
 for (w,o),rows,glyphs in zip(locations,masters,compiled):
  path=(OUT/'masters' if production else OUT)/f'w{w}-o{o}/master.ttf';font=static(rows,glyphs,path,w,o,win_ascent=win_ascent,win_descent=win_descent)
  if o==14:static_otf(rows,font,OUT/'otf'/f'{STEM}-{STYLES[w]}.otf',cff_ascent,cff_descent)
  source=SourceDescriptor();source.path=str(path);source.name=f'w{w}-o{o}';source.familyName=FAMILY;source.styleName=STYLES[w]+f' Optical {o}';source.location={'Weight':w,'Optical Size':o};source.copyInfo=source.copyLib=source.copyFeatures=(w,o)==(400,14);ds.addSource(source)
 for w,style in STYLES.items():
  instance=InstanceDescriptor();instance.familyName=FAMILY;instance.styleName=style;instance.location={'Weight':w,'Optical Size':14};ds.addInstance(instance)
 ds.write(OUT/f'{STEM}.designspace')
 variable,model,fonts=build_variable(ds)
 # Local supports keep the R's measured stroke from accumulating rounded residuals.
 precise_grid_variations(variable,fonts,locations,['P','R','Racute','uni0156','Rcaron'])
 buildStatTable(variable,[{'tag':'wght','name':'Weight','values':[{'value':w,'name':style,'flags':2 if w==400 else 0} for w,style in STYLES.items()]},{'tag':'opsz','name':'Optical Size','values':[{'value':9,'name':'Text'},{'value':14,'name':'Regular Optical','flags':2},{'value':72,'name':'Large'}]}],macNames=False)
 variable.recalcTimestamp=False;variable['head'].created=TIMESTAMP;variable['head'].modified=TIMESTAMP
 variable_dir=OUT/'variable' if production else OUT;variable_dir.mkdir(parents=True,exist_ok=True);variable_stem=f'{STEM}[wght,opsz]' if production else f'{STEM}-Variable'
 for flavor,suffix in [(None,'ttf'),('woff2','woff2')]:variable.flavor=flavor;variable.save(variable_dir/f'{variable_stem}.{suffix}')
 variable=TTFont(variable_dir/f'{variable_stem}.ttf',recalcTimestamp=False)
 static_dir=OUT/'static' if production else OUT;static_dir.mkdir(parents=True,exist_ok=True)
 for w,style in STYLES.items():
  font=instantiateVariableFont(variable,{'wght':w,'opsz':14},inplace=False,updateFontNames=True);font.recalcTimestamp=False;font.flavor=None;font.save(static_dir/f'{STEM}-{style}.ttf');font.flavor='woff2';font.save(static_dir/f'{STEM}-{style}.woff2')
 paths=[Path(__file__),FEATURES,*sorted(source_path.rglob('*'))]
 if production:paths += [ROOT/'sources/config.toml',ROOT/'sources/provenance.json']
 inputs={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()}
 outputs=[p for p in (OUT.rglob('*') if production else OUT.glob(STEM+'-*')) if p.is_file() and p.suffix in ('.ttf','.otf','.woff2') and (not production or p.parent in (variable_dir,static_dir,OUT/'otf'))]
 manifest={'stage':'production','referenceSha256':DELIVERY['referenceSha256'],'characters':''.join(chr(cp) for cp in sorted(variable.getBestCmap())),'glyphs':len(variable.getGlyphOrder()),'locations':[{'wght':w,'opsz':o} for w,o in locations],'inputs':inputs,'python':platform.python_version(),'tools':{n:importlib.metadata.version(n) for n in ['fonttools','glyphsLib','brotli']},'outputs':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(outputs)},'scope':'Fresh outlines, metrics, layout and variation. Appearance acceptance and release are separate.'}
 (OUT/'input-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
 print('Built the variable font and eight static weights in TTF and CFF OTF.')

def main():
 global OUT,STEM,FEATURES,FAMILY,DELIVERY
 DELIVERY=tomllib.loads((ROOT/'sources/config.toml').read_text());OUT=(ROOT/'sources'/DELIVERY['outputDir']).resolve();FAMILY=DELIVERY['familyName'];STEM=''.join(c for c in FAMILY if c.isalnum());FEATURES=ROOT/'sources'/DELIVERY['features'];family()

if __name__=='__main__':main()
