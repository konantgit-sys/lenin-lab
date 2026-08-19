/* B1 */
document.write(new Date().getFullYear())

/* B2 */
var API='/api';
var YEARS=[1893,1895,1898,1899,1901,1902,1903,1905,1906,1907,1908,1909,1910,1911,1912,1913,1914,1915,1916,1917,1918,1919,1920,1921,1922];
var engines=[{id:1,name:'Хроно-разметка',metric:'169 067 параграфов, 55 томов, 3 периода'},{id:2,name:'Концептуальный граф',metric:'206 концептов, 12 735 рёбер, 8 кластеров'},{id:3,name:'Диалектический парсер',metric:'24 781 триада, 11.5% с синтезом'},{id:4,name:'Карта оппонентов',metric:'29 оппонентов, 9 262 упоминания'},{id:5,name:'Машина времени',metric:'4 формата дат, 31 событие'},{id:6,name:'Риторический отпечаток',metric:'5 осей: сарказм → агрессия'},{id:7,name:'500 позиций Ленина',metric:'518 тем, 14 категорий'},{id:8,name:'Цитатомёт',metric:'5 000 цитат, скор до 18.0'},{id:9,name:'Сравнительный анализатор',metric:'62 темы: Маркс/Энгельс vs Ленин'}];
var maxParagraphs=39727,OPP_DATA=null,CONCEPT_NODES=null,engineData=null;
function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open');document.getElementById('sidebar-overlay').classList.toggle('show')}
function switchInstrTab(btn, level) {
  document.querySelectorAll('.instr-tab').forEach(function(t){t.classList.remove('active')});
  btn.classList.add('active');
  document.querySelectorAll('.instr-section').forEach(function(s){s.style.display='none'});
  var sec = document.querySelector('.instr-section[data-instr="'+level+'"]');
  if(sec) sec.style.display='block';
}

function toggleGroup(el){el.parentElement.classList.toggle('collapsed');var g=el.parentElement;var expanded=!g.classList.contains('collapsed');el.setAttribute('aria-expanded',expanded)}

document.getElementById('sidebar').addEventListener('click',function(e){
  var el=e.target.closest('.side-item');
  if(el){var tab=el.getAttribute('data-tab');if(tab!==null){switchTab(parseInt(tab));return}}
  el=e.target.closest('.side-group-label');
  if(el){toggleGroup(el);return}
});

function switchTab(id){
  // 1. Deactivate all items and panels — update aria-current
  document.querySelectorAll('.side-item').forEach(function(s){s.classList.remove('active');s.removeAttribute('aria-current')});
  document.querySelectorAll('.tab-panel').forEach(function(p){p.classList.remove('active')});
  
  // 2. Find and activate the target sidebar item
  var si=document.querySelector('.side-item[data-tab="'+id+'"]');
  if(!si) return;
  si.classList.add('active');
  si.setAttribute('aria-current','page');
  
  // 3. Expand parent group if collapsed
  var group=si.closest('.side-group');
  if(group && group.classList.contains('collapsed')){
    group.classList.remove('collapsed');
  }
  
  // 4. Scroll sidebar item into view
  requestAnimationFrame(function(){
    si.scrollIntoView({block:'nearest',behavior:'instant'});
  });
  
  // 5. Show the target panel
  var p=document.getElementById('panel-'+id);
  if(p){
    p.classList.add('active');
    if(window.innerWidth < 768){
      setTimeout(function(){ p.scrollIntoView({behavior:'smooth',block:'start'}); }, 100);
    }
    // Lazy-load iframe: set src from data-src on first activation
    var ifr=p.querySelector('iframe[data-src]');
    if(ifr && !ifr.src){
      ifr.addEventListener('load',function(){ifr.classList.add('loaded')});
      ifr.src=ifr.getAttribute('data-src');
      ifr.removeAttribute('data-src');
    }
  }
  if(id===2&&!window._timelineInit)initTimeline();if(id===3&&!window._rhetoricInit)initRhetoric();
  if(id===4&&!window._quotesInit){showPanelSkeleton(4);initQuotes()};if(id===5&&!window._enginesInit){showPanelSkeleton(5);initEngines()};
  if(id===6&&!window._conceptsInit)initConcepts();if(id===7&&!window._opponentsInit){showPanelSkeleton(7);initOpponents()};
  if(id===8&&!window._compInit)initComparative();if(id===9&&!window._tomoInit)initTomography();
  if(id===10&&!window._phantomsInit){showPanelSkeleton(10);initPhantoms()};if(id===11&&!window._entropyInit){showPanelSkeleton(11);initEntropy()};
  if(window.innerWidth<768){document.getElementById('sidebar').classList.remove('open');document.getElementById('sidebar-overlay').classList.remove('show')}}

function showPanelSkeleton(panelId){
  var map={4:'skel-quotes',5:'skel-engines',7:'skel-opp',8:'skel-comp',9:'skel-tomo',10:'skel-phant',11:'skel-entr'};
  var sid=map[panelId];if(sid){var el=document.getElementById(sid);if(el)el.style.display=''}
}
function hidePanelSkeleton(panelId){
  var map={4:'skel-quotes',5:'skel-engines',7:'skel-opp',8:'skel-comp',9:'skel-tomo',10:'skel-phant',11:'skel-entr'};
  var sid=map[panelId];if(sid){var el=document.getElementById(sid);if(el)el.style.display='none'}
}
function globalSearch(){var q=document.getElementById('global-search-input').value.trim();if(!q){switchTab(1);return}switchTab(1);document.getElementById('search-input').value=q;setTimeout(function(){doSearch()},150)}
async function fAPI(path){try{var r=await fetch(API+path);return r.json()}catch(e){return null}}
function initSearch(){document.getElementById('search-btn').onclick=doSearch;document.getElementById('search-input').onkeydown=function(e){if(e.key==='Enter')doSearch()}}
async function doSearch(){var q=document.getElementById('search-input').value.trim();if(!q)return;var btn=document.getElementById('search-btn'),res=document.getElementById('search-results');btn.disabled=true;btn.innerHTML='<span class="spinner"></span>';res.innerHTML='';var data=await fAPI('/search?q='+encodeURIComponent(q));btn.disabled=false;btn.textContent='Найти';if(!data||!data.results){res.innerHTML='<p class="empty-state">Ошибка</p>';return}var labels={paragraphs:'Параграфы',positions:'Позиции',quotes:'Цитаты',opponents:'Оппоненты',comparative:'Сравнения',triads:'Триады'};var html='<div style="font-size:11px;color:var(--text-muted);text-align:center;margin-bottom:12px">Найдено в '+data.engines_hit+' движках по запросу &laquo;'+q+'&raquo;</div>';for(var e in data.results){var items=data.results[e];if(!items||!items.length)continue;html+='<div class="sr-block"><div class="sr-label">'+(labels[e]||e)+' ('+items.length+')</div>';for(var i=0;i<Math.min(items.length,5);i++){var item=items[i],year=item.year?'<span class="year">'+item.year+'</span>':'',score=item.score?' <span class="score">скор '+item.score+'</span>':'',topic=item.topic?'<strong class="c-accent">'+item.topic+'</strong>: ':'',text=(item.text||item.pattern||'').substring(0,200);html+='<div class="sr-item">'+year+topic+text+(text.length>=200?'...':'')+score+'</div>'}html+='</div>'}res.innerHTML=html||'<p class="empty-state">Ничего не найдено</p>'}
function initTimeline(){window._timelineInit=true;renderYearPills();populateYearSelects();showTimeline(1917)}
function renderYearPills(){var pills=document.getElementById('year-pills');var HISTORICAL={1905:'Революция 1905',1914:'Начало ПМВ',1917:'Февраль+Октябрь',1921:'НЭП'};YEARS.forEach(function(y){var cls='year-pill';if(HISTORICAL[y])cls+=' yr-historical';pills.innerHTML+='<span class="year-pill '+cls+'" data-year="'+y+'" onclick="showTimeline('+y+',this)" title="'+(HISTORICAL[y]||'')+'">'+y+'</span>'});if(!document.getElementById('hist-legend')){var leg=document.createElement('div');leg.id='hist-legend';leg.style.cssText='text-align:center;margin-top:8px;font-size:9px;color:var(--text-muted);display:flex;gap:10px;justify-content:center;flex-wrap:wrap';leg.innerHTML='<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#c44;opacity:.7"></span> 1905 Революция &nbsp;<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#d4af37;opacity:.7"></span> 1914 ПМВ &nbsp;<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#c41e1e;opacity:.9"></span> 1917 Революция &nbsp;<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4a8;opacity:.7"></span> 1921 НЭП';pills.parentNode.insertBefore(leg,pills.nextSibling)}}
async function showTimeline(year,el){if(el){document.querySelectorAll('#panel-2 .year-pill').forEach(function(p){p.classList.remove('active')});el.classList.add('active')}else{var d=document.querySelector('#panel-2 .year-pill[data-year="'+year+'"]');if(d)d.classList.add('active')}var detail=document.getElementById('tl-detail');detail.innerHTML='<p style="color:var(--text-muted);text-align:center"><span class="spinner"></span> Загрузка...</p>';var data=await fAPI('/timeline?year='+year);if(!data){detail.innerHTML='<p class="c-666">Ошибка</p>';return}var HIST={1905:'Первая русская революция. Кровавое воскресенье, восстание на Потёмкине, декабрьское вооружённое восстание в Москве',1914:'Начало Первой мировой войны. Крах II Интернационала. Ленин в эмиграции пишет о превращении войны империалистической в гражданскую',1917:'Февральская революция → Октябрьский переворот. 39&thinsp;727 параграфов — больше, чем за любые три других года вместе',1921:'Новая экономическая политика (НЭП). Кронштадтское восстание. X съезд РКП(б) — запрет фракций'};var hb=HIST[year]?'<div style="background:linear-gradient(135deg,rgba(200,60,60,.08),rgba(200,60,60,.02));border:1px solid rgba(200,60,60,.15);border-left:3px solid #c44;border-radius:4px;padding:10px 14px;margin-bottom:16px;font-size:11px;color:var(--text-secondary);line-height:1.6"><strong style="color:#d44">'+year+' год</strong> — '+HIST[year]+'</div>':'';var paras=data.paragraphs||0,barPct=Math.min(100,(paras/maxParagraphs)*100),qHtml='';if(data.top_quotes&&data.top_quotes.length){qHtml=data.top_quotes.map(function(q){var t=(q.text||'').substring(0,180);return'<div class="tl-quote">&laquo;'+t+(t.length>=180?'...':'')+'&raquo; <span style="color:var(--text-muted);font-size:10px">(скор '+(q.score||0)+')</span></div>'}).join('')}detail.innerHTML=hb+'<div class="tl-stats"><div class="tl-stat"><div class="tl-num">'+paras.toLocaleString()+'</div><div class="tl-label">Параграфов</div></div><div class="tl-stat"><div class="tl-num">'+(data.positions||0)+'</div><div class="tl-label">Позиций</div></div><div class="tl-stat"><div class="tl-num">'+(data.quotes||0)+'</div><div class="tl-label">Цитат</div></div><div class="tl-stat"><div class="tl-num">'+(data.triads||0)+'</div><div class="tl-label">Триад</div></div></div><div class="tl-chart"><div class="tl-bar" style="width:'+barPct+'%"></div></div>'+qHtml+'<div style="font-size:11px;color:var(--text-muted);margin-top:8px">Тома: '+(data.volumes||[]).join(', ')+'</div>'}
function populateYearSelects(){var a=document.getElementById('year-a'),b=document.getElementById('year-b');YEARS.forEach(function(y,i){a.innerHTML+='<option value="'+y+'"'+(y===1905?' selected':'')+'>'+y+'</option>';b.innerHTML+='<option value="'+y+'"'+(y===1917?' selected':'')+'>'+y+'</option>'})}
async function compareYears(){var ya=document.getElementById('year-a').value,yb=document.getElementById('year-b').value,res=document.getElementById('compare-result');res.innerHTML='<p class="tc"><span class="spinner"></span></p>';var[da,db]=await Promise.all([fAPI('/timeline?year='+ya),fAPI('/timeline?year='+yb)]);if(!da||!db){res.innerHTML='<p class="c-666">Ошибка</p>';return}function bw(v){return Math.min(100,(v/maxParagraphs)*100)}res.innerHTML='<div class="compare-grid"><div class="c-card"><h5>'+ya+'</h5><div class="c-stat"><div><div class="c-num">'+(da.paragraphs||0).toLocaleString()+'</div><div class="c-label">Параграфов</div></div><div><div class="c-num">'+(da.quotes||0)+'</div><div class="c-label">Цитат</div></div><div><div class="c-num">'+(da.triads||0)+'</div><div class="c-label">Триад</div></div></div><div class="tl-chart" style="margin:8px 0"><div class="tl-bar" style="width:'+bw(da.paragraphs||0)+'%"></div></div><div class="fs-xs">Тома: '+(da.volumes||[]).slice(0,5).join(', ')+'</div></div><div class="c-card"><h5>'+yb+'</h5><div class="c-stat"><div><div class="c-num">'+(db.paragraphs||0).toLocaleString()+'</div><div class="c-label">Параграфов</div></div><div><div class="c-num">'+(db.quotes||0)+'</div><div class="c-label">Цитат</div></div><div><div class="c-num">'+(db.triads||0)+'</div><div class="c-label">Триад</div></div></div><div class="tl-chart" style="margin:8px 0"><div class="tl-bar" style="width:'+bw(db.paragraphs||0)+'%"></div></div><div class="fs-xs">Тома: '+(db.volumes||[]).slice(0,5).join(', ')+'</div></div></div>';res.scrollIntoView({behavior:'smooth'})}
function initRhetoric(){window._rhetoricInit=true;var p=RHETORIC.global_profile;document.getElementById('rhetoric-profile').innerHTML='<h4 style="text-align:center;margin-bottom:10px;color:var(--text-secondary);font-size:12px">Глобальный профиль (169 067 параграфов)</h4><div class="rhet-bars"><div class="bar-item"><div class="bar-fill"><div class="bar-inner" style="height:'+(p.sarcasm*100)+'%;background:linear-gradient(180deg,#d4af37,#b8960c)"></div></div><div class="fs-xs">Сарказм</div><div style="font-size:15px;color:#b8960c;font-weight:700">'+(p.sarcasm*100).toFixed(0)+'%</div></div><div class="bar-item"><div class="bar-fill"><div class="bar-inner" style="height:'+(p.aggression*100)+'%;background:linear-gradient(180deg,#c41e1e,#660000)"></div></div><div class="fs-xs">Агрессия</div><div style="font-size:15px;color:#c44;font-weight:700">'+(p.aggression*100).toFixed(0)+'%</div></div><div class="bar-item"><div class="bar-fill"><div class="bar-inner" style="height:'+(p.analytical*100)+'%;background:linear-gradient(180deg,#888,#666)"></div></div><div class="fs-xs">Анализ</div><div style="font-size:15px;color:#888;font-weight:700">'+(p.analytical*100).toFixed(0)+'%</div></div><div class="bar-item"><div class="bar-fill"><div class="bar-inner" style="height:'+(p.inspiration*100)+'%;background:linear-gradient(180deg,#4a8,#3a7)"></div></div><div class="fs-xs">Вдохн.</div><div style="font-size:15px;color:#4a8;font-weight:700">'+(p.inspiration*100).toFixed(0)+'%</div></div><div class="bar-item"><div class="bar-fill"><div class="bar-inner" style="height:'+(p.contempt*100)+'%;background:linear-gradient(180deg,#999,#777)"></div></div><div class="fs-xs">Презр.</div><div style="font-size:15px;color:var(--text-secondary);font-weight:700">'+(p.contempt*100).toFixed(1)+'%</div></div></div>';var svg=document.getElementById('arc-data'),arc=RHETORIC.emotional_arc;if(!arc.length)return;var stepX=560/(arc.length-1),maxD=Math.max.apply(null,arc.map(function(a){return a.density}));for(var i=0;i<=4;i++){var gy=20+200-(200*i/4);svg.innerHTML+='<line x1="50" y1="'+gy+'" x2="610" y2="'+gy+'" stroke="#1e1e28" stroke-width="0.5" stroke-dasharray="4,4"/>';svg.innerHTML+='<text x="45" y="'+(gy+3)+'" fill="#444" font-size="9" text-anchor="end">'+(maxD*i/4).toFixed(1)+'</text>'}var dPath='';arc.forEach(function(a,i){var sx=50+i*stepX,sy=20+200-(a.density/maxD)*200;dPath+=(i===0?'M':'L')+' '+sx.toFixed(0)+' '+sy.toFixed(0)});var areaPath=dPath+' L '+(50+(arc.length-1)*stepX).toFixed(0)+' 220 L 50 220 Z';svg.innerHTML+='<path d="'+areaPath+'" fill="url(#gA)" opacity="0.1"/><path d="'+dPath+'" fill="none" stroke="#c44" stroke-width="2.5"/>';var prevDom='';arc.forEach(function(a,i){var sx=50+i*stepX,sy=20+200-(a.density/maxD)*200,color=a.dominant==='sarcasm'?'#d4af37':'#c41e1e';svg.innerHTML+='<circle cx="'+sx.toFixed(0)+'" cy="'+sy.toFixed(0)+'" r="4" fill="'+color+'" opacity="0.8"/>';if(a.dominant!==prevDom&&prevDom!==''&&a.dominant==='aggression'){svg.innerHTML+='<line x1="'+sx.toFixed(0)+'" y1="20" x2="'+sx.toFixed(0)+'" y2="220" stroke="#c44" stroke-width="1" stroke-dasharray="6,3" opacity="0.3"/>'}prevDom=a.dominant});var labels=document.getElementById('arc-labels');[1893,1900,1905,1910,1915,1917,1919,1922].forEach(function(yr){var idx=arc.findIndex(function(a){return a.year===yr});if(idx>=0)labels.innerHTML+='<text x="'+(50+idx*stepX).toFixed(0)+'" y="238" fill="#555" font-size="10" text-anchor="middle">'+yr+'</text>'});document.getElementById('arc-legend').innerHTML='<span style="display:inline-block;width:10px;height:10px;background:#d4af37;border-radius:50%;margin-right:4px"></span><span style="color:var(--text-secondary);font-size:10px">Сарказм</span> <span style="display:inline-block;width:10px;height:10px;background:#c41e1e;border-radius:50%;margin-left:12px;margin-right:4px"></span><span style="color:var(--text-secondary);font-size:10px">Агрессия</span>';var sarcYears=arc.filter(function(a){return a.dominant==='sarcasm'}).length,aggYears=arc.filter(function(a){return a.dominant==='aggression'}).length,pivot=arc.find(function(a){return a.dominant==='aggression'});document.getElementById('arc-insights').innerHTML='<strong class="c-gold">1893&ndash;'+(pivot?pivot.year-1:1918)+':</strong> сарказм ('+sarcYears+' лет) &nbsp;|&nbsp; <strong class="c-accent">'+(pivot?pivot.year:1919)+'&ndash;1922:</strong> агрессия ('+aggYears+' года) | Пик: '+arc.reduce(function(a,b){return a.density>b.density?a:b}).year+' ('+maxD.toFixed(2)+')'}
function initQuotes(){window._quotesInit=true;populateQuoteYears();loadQuotes()}
function populateQuoteYears(){var sel=document.getElementById('q-year');YEARS.forEach(function(y){sel.innerHTML+='<option value="'+y+'">'+y+'</option>'})}
var quotesPage=0,allQuotesCache=[];
async function loadQuotes(more){if(!more){quotesPage=0;allQuotesCache=[]}var feed=document.getElementById('quote-feed');if(!more){showPanelSkeleton(4);feed.innerHTML='<p class="tc"><span class="spinner"></span> Загрузка...</p>';var seeds=['революция','партия','класс','диктатура','капитал','борьба','власть','демократия','социализм','государство'],q=seeds[quotesPage%seeds.length],data=await fAPI('/search?q='+encodeURIComponent(q));if(data&&data.results&&data.results.quotes){allQuotesCache=allQuotesCache.concat(data.results.quotes)}var yearFilter=document.getElementById('q-year').value,sort=document.getElementById('q-sort').value,filtered=allQuotesCache.slice();if(yearFilter)filtered=filtered.filter(function(q){return q.year==yearFilter});if(sort==='score')filtered.sort(function(a,b){return(b.score||0)-(a.score||0)});else if(sort==='year')filtered.sort(function(a,b){return(b.year||0)-(a.year||0)});else filtered.sort(function(){return Math.random()-0.5});var html='';filtered.slice(0,more?allQuotesCache.length:10).forEach(function(q){html+='<div class="q-item"><div class="q-text">&laquo;'+(q.text||'').substring(0,250)+((q.text||'').length>250?'...':'')+'&raquo;</div><div class="q-meta">'+q.year+' <span class="q-score">скор '+(q.score||0)+'</span></div></div>'});hidePanelSkeleton(4);feed.innerHTML=html||'<p style="color:var(--text-muted);text-align:center">Нет цитат по фильтру</p>';quotesPage++}}
function initEngines(){window._enginesInit=true;var grid=document.getElementById('engine-grid');engines.forEach(function(e){hidePanelSkeleton(5);grid.innerHTML+='<div class="engine-card" id="ecard-'+e.id+'"><div class="e-id">Механика &numero;'+e.id+'</div><div class="e-name">'+e.name+'</div><div class="e-metric">'+e.metric+'</div><div class="e-more" id="emore-'+e.id+'"><span class="c-dim">Клик для деталей...</span></div></div>';document.getElementById('ecard-'+e.id).onclick=function(){toggleEngine(e.id)}})}
async function toggleEngine(id){var card=document.getElementById('ecard-'+id),more=document.getElementById('emore-'+id);card.classList.toggle('expanded');if(card.classList.contains('expanded')&&more.textContent==='Клик для деталей...'){if(!engineData)engineData=await fAPI('/stats');if(engineData&&engineData.engines){var eKey=Object.keys(engineData.engines).find(function(k){return k.startsWith(id+'_')});if(eKey){var d=engineData.engines[eKey],html='';for(var k in d)html+='<div style="margin:3px 0"><span class="e-detail-key">'+k+':</span> '+(typeof d[k]==='number'?d[k].toLocaleString():d[k])+'</div>';more.innerHTML=html}else{more.innerHTML='<span class="c-dim">Нет данных</span>'}}}}
function initConcepts(){window._conceptsInit=true;var legend=document.getElementById('concept-legend'),clusters=CONCEPT_DATA.legend,colors=['#c44','#b8960c','#4a8','#397339','#7b3294','#c66','#0aa','#e67e22','#777','#a44','#2c7','#69c','#a3c','#c96','#4a4','#678'];clusters.forEach(function(cl,i){legend.innerHTML+='<span class="cl-tag" style="color:'+colors[i%colors.length]+';border-color:'+colors[i%colors.length]+'33">'+cl.name+' ('+cl.count+')</span>'});CONCEPT_NODES=[];clusters.forEach(function(cl,ci){cl.concepts.forEach(function(c){CONCEPT_NODES.push({name:c,cluster:ci,clusterName:cl.name})})});drawConceptCanvas()}
var draggedNode=null,hoveredNode=null;
function drawConceptCanvas(){var container=document.getElementById('concept-graph'),canvas=document.getElementById('concept-canvas'),dpr=window.devicePixelRatio||1;canvas.width=container.offsetWidth*dpr;canvas.height=container.offsetHeight*dpr;canvas.style.width=container.offsetWidth+'px';canvas.style.height=container.offsetHeight+'px';var ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);var W=container.offsetWidth,H=container.offsetHeight,colorsArr=['#c44','#b8960c','#4a8','#397339','#7b3294','#c66','#0aa','#e67e22'],positions=[],clusterGroups={};CONCEPT_NODES.forEach(function(n){if(!clusterGroups[n.cluster])clusterGroups[n.cluster]=[];clusterGroups[n.cluster].push(n)});var cKeys=Object.keys(clusterGroups),pad=60,cxCount=Math.ceil(Math.sqrt(cKeys.length)),cyCount=Math.ceil(cKeys.length/cxCount),cw=(W-2*pad)/cxCount,ch=(H-2*pad)/cyCount;cKeys.forEach(function(ck,ci){var cx=pad+(ci%cxCount)*cw,cy=pad+Math.floor(ci/cxCount)*ch,nodes=clusterGroups[ck],r=Math.min(cw,ch)/2-20;nodes.forEach(function(n,ni){var angle=(ni/nodes.length)*Math.PI*2,nx=cx+cw/2+Math.cos(angle)*r*0.7,ny=cy+ch/2+Math.sin(angle)*r*0.7;positions.push({node:n,x:nx,y:ny,cx:cx+cw/2,cy:cy+ch/2,color:colorsArr[parseInt(ck)%colorsArr.length]})})});var sel=document.getElementById('concept-selected');function draw(){ctx.clearRect(0,0,W,H);cKeys.forEach(function(ck,ci){var cx=pad+(ci%cxCount)*cw,cy=pad+Math.floor(ci/cxCount)*ch;ctx.beginPath();ctx.arc(cx+cw/2,cy+ch/2,Math.min(cw,ch)/2-8,0,Math.PI*2);ctx.fillStyle='rgba(200,200,200,0.03)';ctx.fill();ctx.fillStyle='#333';ctx.font='10px Inter';ctx.textAlign='center';var nm=(CONCEPT_DATA.legend[parseInt(ck)]||{}).name||'';ctx.fillText(nm.substring(nm.indexOf('.')+2),cx+cw/2,cy+8)});positions.forEach(function(p){var isHov=hoveredNode===p,r=isHov?8:5;ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fillStyle=p.color;ctx.fill();if(isHov){ctx.strokeStyle='#ddd';ctx.lineWidth=1.5;ctx.stroke()}ctx.fillStyle='#777';ctx.font=(isHov?'bold ':'')+'10px Inter';ctx.textAlign='center';ctx.fillText(p.node.name,p.x,p.y-10)})}canvas.onmousemove=function(e){var rect=canvas.getBoundingClientRect(),mx=e.clientX-rect.left,my=e.clientY-rect.top;hoveredNode=null;for(var i=0;i<positions.length;i++){var dx=mx-positions[i].x,dy=my-positions[i].y;if(dx*dx+dy*dy<100){hoveredNode=positions[i];break}}if(draggedNode){draggedNode.x=mx;draggedNode.y=my}canvas.style.cursor=hoveredNode?'pointer':'default';draw();sel.innerHTML=hoveredNode?'<strong>'+hoveredNode.node.name+'</strong> &mdash; '+hoveredNode.node.clusterName:''};canvas.onclick=function(e){if(hoveredNode)sel.innerHTML='<strong>'+hoveredNode.node.name+'</strong> &mdash; '+hoveredNode.node.clusterName+' <a href="#" onclick="document.getElementById(\'global-search-input\').value=\''+hoveredNode.node.name+'\';switchTab(1);doSearch();return false" class="c-accent">искать</a>'};canvas.onmousedown=function(e){if(hoveredNode)draggedNode=hoveredNode};canvas.onmouseup=function(){draggedNode=null};canvas.onmouseleave=function(){hoveredNode=null;draggedNode=null;draw()};canvas.ontouchstart=function(e){var touch=e.touches[0],rect=canvas.getBoundingClientRect(),mx=touch.clientX-rect.left,my=touch.clientY-rect.top;for(var i=0;i<positions.length;i++){var dx=mx-positions[i].x,dy=my-positions[i].y;if(dx*dx+dy*dy<200){draggedNode=positions[i];break}}};canvas.ontouchmove=function(e){if(draggedNode){var t=e.touches[0],r=canvas.getBoundingClientRect();draggedNode.x=t.clientX-r.left;draggedNode.y=t.clientY-r.top;draw();e.preventDefault()}};canvas.ontouchend=function(){draggedNode=null};draw()}
async function initOpponents(){window._opponentsInit=true;var grid=document.getElementById('opp-grid');if(!OPP_DATA){OPP_DATA=await fAPI('/opponents');if(!OPP_DATA||!OPP_DATA.opponents){OPP_DATA={opponents:[{key:'milyukov',full_name:'Павел Милюков',camp:'кадеты',total_mentions:4168,peak_year:1908,top_topics:'конституция, война, демократия'},{key:'esers',full_name:'Партия эсеров',camp:'эсеры',total_mentions:2525,peak_year:1918,top_topics:'террор, аграрный вопрос, Учредительное собрание'},{key:'mach',full_name:'Эрнст Мах',camp:'махизм',total_mentions:775,peak_year:1911,top_topics:'эмпириокритицизм, ощущение, материя'},{key:'bernstein',full_name:'Эдуард Бернштейн',camp:'ревизионизм',total_mentions:669,peak_year:1917,top_topics:'реформы, социализм, демократия'},{key:'plekhanov',full_name:'Георгий Плеханов',camp:'меньшевики',total_mentions:249,peak_year:1917,top_topics:'марксизм, диалектика, война'},{key:'mensheviks',full_name:'Меньшевики',camp:'меньшевики',total_mentions:220,peak_year:1917,top_topics:'коалиция, советы, выборы'},{key:'kautsky',full_name:'Карл Каутский',camp:'центризм',total_mentions:180,peak_year:1918,top_topics:'диктатура, демократия, империализм'},{key:'liberals',full_name:'Либералы (кадеты)',camp:'кадеты',total_mentions:160,peak_year:1907,top_topics:'Дума, конституция, свобода'},{key:'anarchists',full_name:'Анархисты',camp:'анархизм',total_mentions:95,peak_year:1918,top_topics:'государство, власть, самоуправление'},{key:'trotsky',full_name:'Лев Троцкий',camp:'большевики',total_mentions:85,peak_year:1918,top_topics:'армия, мир, бюрократия'}],links:[],disputes:[]}}}var opps=OPP_DATA.opponents||[],maxM=Math.max.apply(null,opps.map(function(o){return o.total_mentions||0}));grid.innerHTML='';opps.forEach(function(o){var sz=11+((o.total_mentions||0)/maxM)*9;grid.innerHTML+='<div class="opp-node" onclick="showOpponent(\''+o.key+'\')" style="border-left:3px solid hsl('+((o.total_mentions/maxM)*20)+',60%,35%)"><div class="o-name" style="font-size:'+sz+'px">'+o.full_name+'</div><div class="o-mentions">'+(o.total_mentions||0).toLocaleString()+' упоминаний &middot; пик '+o.peak_year+'</div><div class="o-camp">'+o.camp+'</div></div>'});hidePanelSkeleton(7)}
function showOpponent(key){var o=(OPP_DATA.opponents||[]).find(function(x){return x.key===key});if(!o)return;var d=document.getElementById('opp-detail');d.innerHTML='<div style="text-align:right;cursor:pointer;color:var(--text-muted)" onclick="this.parentElement.classList.remove(\'show\')">&times;</div><div class="od-name">'+o.full_name+'</div><div class="od-stats"><strong>Лагерь:</strong> '+o.camp+'<br><strong>Упоминаний:</strong> '+(o.total_mentions||0).toLocaleString()+'<br><strong>Пик:</strong> '+o.peak_year+'<br><strong>Темы:</strong> '+o.top_topics+'</div>';d.classList.add('show');d.scrollIntoView({behavior:'smooth'})}
async function initComparative(){window._compInit=true;var list=document.getElementById('comp-list');list.innerHTML='<p class="tc"><span class="spinner"></span> Загрузка...</p>';var data=await fAPI('/search?q=диктатура%20революция%20государство%20класс%20партия'),items=data&&data.results&&data.results.comparative?data.results.comparative:[];if(!items.length){list.innerHTML='<p class="tc">Используйте поиск для сравнений Маркс/Энгельс vs Ленин.</p>';hidePanelSkeleton(8);return}var html='';items.forEach(function(item){html+='<div class="comp-item" onclick="this.classList.toggle(\'open\')"><div class="comp-topic">'+item.topic+'</div><div class="comp-body"><div class="comp-col"><strong>Эволюция:</strong> '+(item.evolution||'От Маркса и Энгельса к Ленину.')+'</div></div></div>'});list.innerHTML=html;hidePanelSkeleton(8)}
function initTomography(){window._tomoInit=true;function yearColor(y){var idx=YEARS.indexOf(y);if(idx<0)return'#555';var t=idx/(YEARS.length-1),r=Math.round(40+t*200),g=Math.round(80+(1-Math.abs(t-0.5)*2)*150),b=Math.round(200-t*180);return'rgb('+r+','+g+','+b+')'}var legend=document.getElementById('tomo-legend');for(var i=0;i<YEARS.length;i+=2){legend.innerHTML+='<span style="display:inline-block;width:14px;height:14px;background:'+yearColor(YEARS[i])+';border-radius:2px;margin:0 1px" title="'+YEARS[i]+'"></span>'}legend.innerHTML+=' <span style="font-size:9px;color:var(--text-muted);margin-left:4px">1893</span>';for(var i=YEARS.length-2;i<YEARS.length;i++){legend.innerHTML+='<span style="display:inline-block;width:14px;height:14px;background:'+yearColor(YEARS[i])+';border-radius:2px;margin:0 1px" title="'+YEARS[i]+'"></span>'}legend.innerHTML+=' <span style="font-size:9px;color:var(--text-muted);margin-left:4px">1922</span>';var container=document.getElementById('tomo-container'),canvas=document.getElementById('tomo-canvas'),tooltip=document.getElementById('tomo-tooltip'),detail=document.getElementById('tomo-detail'),dpr=window.devicePixelRatio||1,cw=container.offsetWidth,ch=container.offsetHeight;canvas.width=cw*dpr;canvas.height=ch*dpr;canvas.style.width=cw+'px';canvas.style.height=ch+'px';var ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);var allPoints=null,hoverPoint=null;function draw(){if(!allPoints)return;ctx.clearRect(0,0,cw,ch);ctx.fillStyle='#0d0d0d';ctx.fillRect(0,0,cw,ch);for(var i=0;i<allPoints.length;i++){var p=allPoints[i],px=p[0],py=p[1],yr=p[2];ctx.fillStyle=yearColor(yr);ctx.globalAlpha=0.35;ctx.fillRect(px-1.5,py-1.5,3,3)}ctx.globalAlpha=1;if(hoverPoint){ctx.fillStyle='#fff';ctx.globalAlpha=0.9;ctx.beginPath();ctx.arc(hoverPoint[0],hoverPoint[1],6,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();ctx.globalAlpha=1}ctx.fillStyle='rgba(255,255,255,0.25)';ctx.font='10px Inter';ctx.textAlign='center';ctx.fillText('1893',30,ch-10);ctx.fillText('1922',cw-30,ch-10)}fetch('/tomography_compact.json').then(function(r){return r.json()}).then(function(data){allPoints=data;var xs=[],ys=[];for(var i=0;i<Math.min(data.length,500);i++){xs.push(data[i][0]);ys.push(data[i][1])}var xmin=Math.min.apply(null,xs),xmax=Math.max.apply(null,xs),ymin=Math.min.apply(null,ys),ymax=Math.max.apply(null,ys),xr=(xmax-xmin)||1,yr=(ymax-ymin)||1,pad=30;for(var i=0;i<data.length;i++){data[i][0]=pad+((data[i][0]-xmin)/xr)*(cw-2*pad);data[i][1]=pad+((data[i][1]-ymin)/yr)*(ch-2*pad)}draw()}).catch(function(){detail.innerHTML='<span class="c-dim">Данные загружаются... (файл ~160 KB)</span>'});canvas.onmousemove=function(e){if(!allPoints)return;var rect=canvas.getBoundingClientRect(),mx=e.clientX-rect.left,my=e.clientY-rect.top;hoverPoint=null;var minD=25;for(var i=0;i<allPoints.length;i++){var dx=mx-allPoints[i][0],dy=my-allPoints[i][1];if(dx*dx+dy*dy<minD){hoverPoint=allPoints[i];minD=dx*dx+dy*dy}}if(hoverPoint){tooltip.style.opacity='1';tooltip.style.left=(mx+12)+'px';tooltip.style.top=(my-20)+'px';tooltip.textContent='Год: '+hoverPoint[2];detail.innerHTML='<span class="c-accent">'+hoverPoint[2]+' год</span>'}else{tooltip.style.opacity='0';detail.innerHTML=''}draw()}}
function initPhantoms(){window._phantomsInit=true;var data=null;fetch('/api/phantoms').then(function(r){return r.json()}).then(function(d){if(!d||!d.by_year)return;data=d;var pills=document.getElementById('phantom-years'),years=Object.keys(d.by_year).sort(function(a,b){return a-b});years.forEach(function(y){pills.innerHTML+='<span class="year-pill" data-year="'+y+'" onclick="showPhantoms(\''+y+'\',this)">'+y+' ('+d.by_year[y].length+')</span>'});if(years.length>0){var first=document.querySelector('#phantom-years .year-pill');if(first)showPhantoms(years[0],first)}}).catch(function(){document.getElementById('phantom-list').innerHTML='<p style=\"color:#c44;text-align:center;padding:20px\">API временно недоступен. Попробуйте позже.</p>'});window.showPhantoms=function(year,el){if(!data)return;document.querySelectorAll('#phantom-years .year-pill').forEach(function(p){p.classList.remove('active')});if(el)el.classList.add('active');var items=data.by_year[year]||[],list=document.getElementById('phantom-list'),html='';items.forEach(function(item,i){var marker=item.marker.replace('...','').replace(',','');html+='<div class="comp-item" onclick="this.classList.toggle(\'open\')"><div class="comp-topic">&numero;'+(i+1)+' &laquo;'+marker+'&raquo; &mdash; том '+item.volume+'</div><div class="comp-body"><div style="font-size:11px;color:var(--text-muted);margin-bottom:6px">Глава: '+(item.chapter||'&mdash;')+'</div><div class="comp-col"><strong>Аргумент фантома:</strong> '+(item.phantom_argument||'')+'</div><div class="comp-col" style="margin-top:8px"><strong>Контекст:</strong> ...'+(item.context||'')+'...</div></div></div>'});list.innerHTML=html||'<p class="empty-state">Нет данных</p>';var sk=document.getElementById('skel-phant');if(sk)sk.style.display='none'}}
function initEntropy(){window._entropyInit=true;var svgData=document.getElementById('entropy-data'),svgLabels=document.getElementById('entropy-labels'),svgBars=document.getElementById('entropy-bars'),detail=document.getElementById('entropy-detail');fetch('/api/entropy').then(function(r){return r.json()}).then(function(d){if(!d||!d.data)return;var data=d.data,maxE=d.data.reduce(function(a,b){return Math.max(a,b.entropy)},0),minE=d.data.reduce(function(a,b){return Math.min(a,b.entropy)},999),maxM=d.data.reduce(function(a,b){return Math.max(a,b.max_entropy)},0),stepX=640/(data.length-1);for(var i=0;i<=4;i++){var gy=20+240-(240*i/4);svgData.innerHTML+='<line x1="60" y1="'+gy+'" x2="700" y2="'+gy+'" stroke="#1e1e28" stroke-width="0.5" stroke-dasharray="4,4"/>';svgData.innerHTML+='<text x="55" y="'+(gy+4)+'" fill="#444" font-size="9" text-anchor="end">'+(minE+(maxE-minE)*i/4).toFixed(2)+'</text>'}var maxPath='';data.forEach(function(d,i){var sx=60+i*stepX,sy=20+240-((d.max_entropy-minE)/(maxE-minE+0.01))*240;maxPath+=(i===0?'M':'L')+' '+sx.toFixed(0)+' '+sy.toFixed(0)});svgData.innerHTML+='<path d="'+maxPath+'" fill="none" stroke="#2a2a33" stroke-width="1" stroke-dasharray="8,4" opacity="0.5"/>';var ePath='';data.forEach(function(d,i){var sx=60+i*stepX,sy=20+240-((d.entropy-minE)/(maxE-minE+0.01))*240;ePath+=(i===0?'M':'L')+' '+sx.toFixed(0)+' '+sy.toFixed(0)});var areaPath=ePath+' L '+(60+(data.length-1)*stepX).toFixed(0)+' 260 L 60 260 Z';svgData.innerHTML+='<path d="'+areaPath+'" fill="url(#gEnt)" opacity="0.12"/><path d="'+ePath+'" fill="none" stroke="#c44" stroke-width="2.5"/>';[1893,1900,1905,1910,1915,1917,1919,1922].forEach(function(yr){var idx=data.findIndex(function(d){return d.year===yr});if(idx>=0)svgLabels.innerHTML+='<text x="'+(60+idx*stepX).toFixed(0)+'" y="275" fill="#555" font-size="10" text-anchor="middle">'+yr+'</text>'});data.forEach(function(d,i){var sx=60+i*stepX,bh=(d.entropy/maxE)*240,color=d.entropy>5.4?'#c44':d.entropy>5.1?'#e67e22':'#4a8';svgBars.innerHTML+='<div style="flex:1;min-width:0;display:flex;align-items:flex-end;justify-content:center"><div style="width:65%;height:'+bh+'px;background:'+color+';opacity:0.5;border-radius:2px 2px 0 0;min-height:2px;transition:height .3s" title="'+d.year+': '+d.entropy.toFixed(3)+'"></div></div>'});var hi=data.reduce(function(a,b){return a.entropy>b.entropy?a:b}),lo=data.reduce(function(a,b){return a.entropy<b.entropy?a:b});detail.innerHTML='<strong class="c-accent">Макс. энтропия:</strong> '+hi.year+' ('+hi.entropy.toFixed(3)+') &mdash; разнообразие тем | <strong style="color:#4a8">Мин.:</strong> '+lo.year+' ('+lo.entropy.toFixed(3)+') &mdash; фокус на '+(lo.dominant_cluster||'одной теме')+' | <strong>1911:</strong> '+data.find(function(d){return d.year===1911}).entropy.toFixed(3)+' &mdash; провал (&laquo;Материализм и эмпириокритицизм&raquo;)';hidePanelSkeleton(11)}).catch(function(){hidePanelSkeleton(11);detail.innerHTML='<span style=\"color:#c44\">API временно недоступен</span>'})}
// ═══ I18N INIT ═══
I18N.init();
// ═══ PATHWAY RUNNER ═══
function runPathway(type){
  var steps={
    imperialism:[{tab:2,delay:300,action:function(){var y=document.querySelector('#panel-2 .year-pill[data-year="1915"]');if(y)y.click()}},{tab:6,delay:1500},{tab:14,delay:3000}],
    revolution:[{tab:2,delay:300,action:function(){var y=document.querySelector('#panel-2 .year-pill[data-year="1917"]');if(y)y.click()}},{tab:3,delay:2000},{tab:4,delay:3500}],
    philosophy:[{tab:6,delay:300},{tab:14,delay:2000},{tab:1,delay:3500,action:function(){var inp=document.getElementById('search-input');if(inp){inp.value='материя';doSearch()}}}]
  };
  var s=steps[type];if(!s)return;
  var res=document.getElementById('pathway-result');
  res.innerHTML='<div style="text-align:center;padding:20px;color:var(--text-secondary)"><span class="spinner"></span> Запуск маршрута...</div>';
  s.forEach(function(step,i){
    setTimeout(function(){
      switchTab(step.tab);
      setTimeout(function(){if(step.action)step.action()},400);
      if(i===s.length-1)res.innerHTML='<div style="text-align:center;padding:20px;color:#4a8;font-size:13px">Маршрут завершён. Исследуйте дальше!</div>'
    },step.delay)
  })
}
initSearch();fAPI('/stats').then(function(d){if(d)engineData=d});fAPI('/opponents').then(function(d){if(d&&d.opponents)OPP_DATA=d}).catch(function(){console.log('Opponents API unavailable')});
// ═══ THEME TOGGLE ═══
(function(){
  var saved=localStorage.getItem('lenin-theme')||'dark';
  function applyTheme(t){
    var html=document.documentElement;
    if(t==='light'){
      html.classList.add('light');
      html.classList.remove('dark');
      var btn=document.getElementById('theme-toggle-btn');
      if(btn)btn.textContent='тёмная тема';
    } else {
      html.classList.add('dark');
      html.classList.remove('light');
      var btn=document.getElementById('theme-toggle-btn');
      if(btn)btn.textContent='светлая тема';
    }
    localStorage.setItem('lenin-theme',t);
  }
  window.toggleTheme=function(){
    var cur=localStorage.getItem('lenin-theme')||'dark';
    applyTheme(cur==='dark'?'light':'dark');
  };
  applyTheme(saved);
})();
// ═══ VISITOR COUNTER ═══
(function(){
  var key='lenin-visits-'+(new Date()).toISOString().slice(0,7);
  var total=parseInt(localStorage.getItem('lenin-total-visits')||'0');
  if(!localStorage.getItem('lenin-visit-'+key)){
    total+=1;
    localStorage.setItem('lenin-total-visits',String(total));
    localStorage.setItem('lenin-visit-'+key,'1');
  }
  var el=document.getElementById('visit-counter');
  if(el)el.textContent='посещений: '+total;
})();
document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();document.getElementById('global-search-input').focus()}});
// ═══ PARTICLES BACKGROUND ═══
(function(){
  var c=document.getElementById('particles-canvas'),ctx=c.getContext('2d');
  var W,H,dots=[];
  function resize(){W=c.width=window.innerWidth;H=c.height=window.innerHeight}
  resize();window.addEventListener('resize',resize);
  for(var i=0;i<50;i++)dots.push({x:Math.random()*W,y:Math.random()*H,r:Math.random()*1.5+.5,vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,o:Math.random()*.4+.1});
  function loop(){
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<dots.length;i++){
      var d=dots[i];d.x+=d.vx;d.y+=d.vy;
      if(d.x<0)d.x=W;if(d.x>W)d.x=0;if(d.y<0)d.y=H;if(d.y>H)d.y=0;
      ctx.beginPath();ctx.arc(d.x,d.y,d.r,0,Math.PI*2);
      ctx.fillStyle='rgba(200,60,60,'+d.o+')';ctx.fill();
    }
    for(var i=0;i<dots.length;i++){
      for(var j=i+1;j<dots.length;j++){
        var dx=dots[i].x-dots[j].x,dy=dots[i].y-dots[j].y,dist=Math.sqrt(dx*dx+dy*dy);
        if(dist<120){ctx.beginPath();ctx.moveTo(dots[i].x,dots[i].y);ctx.lineTo(dots[j].x,dots[j].y);ctx.strokeStyle='rgba(200,60,60,'+(.04*(1-dist/120))+')';ctx.stroke()}
      }
    }
    requestAnimationFrame(loop);
  }
  loop();
})();
// ═══ CARD MOUSE TRACKING ═══
(function(){
  document.querySelectorAll('.card,.path-card').forEach(function(card){
    card.addEventListener('mousemove',function(e){
      var r=card.getBoundingClientRect();
      card.style.setProperty('--mx',(e.clientX-r.left)+'px');
      card.style.setProperty('--my',(e.clientY-r.top)+'px');
    });
  });
})();
// ═══ SOCIAL SHARE ═══
function copySectionLink(panelId){
  var url=location.origin+location.pathname+'#'+(panelId||'');
  navigator.clipboard.writeText(url).then(function(){
    var el=document.querySelector('.section-link-btn');if(el){el.textContent='Copied!';el.classList.add('copied');setTimeout(function(){el.textContent='Copy link';el.classList.remove('copied')},1500)}
  }).catch(function(){prompt('Copy:',url)});
}
function shareTwitter(text){window.open('https://twitter.com/intent/tweet?text='+encodeURIComponent(text||'Lenin-Book: аналитический корпус 55 томов Ленина'),'share','width=550,height=420')}
function shareTelegram(text){window.open('https://t.me/share/url?url='+encodeURIComponent(location.href)+'&text='+encodeURIComponent(text||'Lenin-Book — аналитический корпус'),'share','width=550,height=420')}
// ═══ ADD SHARE BAR TO PANEL WRAPPERS ═══
(function(){
  var shareHTML='<div class="share-bar"><button class="share-btn" onclick="copySectionLink()"><svg viewBox="0 0 24 24"><rect x="8" y="2" width="8" height="4" rx="1" stroke="currentColor" fill="none" stroke-width="1.5"/><rect x="5" y="8" width="14" height="14" rx="2" stroke="currentColor" fill="none" stroke-width="1.5"/></svg> Copy link</button><button class="share-btn" onclick="shareTwitter()"><svg viewBox="0 0 24 24"><path d="M22 4s-2 1.2-4 2c-1-1-2.5-1.8-4.2-1.8-3.2 0-5.8 2.6-5.8 5.8v1.3c-4.5-.2-7.5-3.3-9-4.8 0 0-1.5 5 3 8.5-1.5 1-4 1.5-5.5 1.5 2 2 5 3 8 3 9 0 13.5-7.5 13.5-13.5v-.6c.9-.7 1.7-1.5 2.3-2.5z" stroke="currentColor" fill="none" stroke-width="1.5"/></svg> Twitter</button><button class="share-btn" onclick="shareTelegram()"><svg viewBox="0 0 24 24"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linejoin="round"/></svg> Telegram</button></div>';
  document.querySelectorAll('.panel-wrap').forEach(function(wrap){
    if(!wrap.querySelector('.share-bar')){var div=document.createElement('div');div.innerHTML=shareHTML;wrap.appendChild(div.firstElementChild)}
  });
})();
// ═══ SCROLL REVEAL (IntersectionObserver) ═══
(function(){
  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if(e.isIntersecting){e.target.classList.add('revealed');observer.unobserve(e.target)}
    });
  },{threshold:.12,rootMargin:'0px 0px -30px 0px'});
  document.querySelectorAll('.reveal,.reveal-scale').forEach(function(el){observer.observe(el)});
  var origSwitch = window.switchTab;
  window.switchTab = function(){
    origSwitch && origSwitch.apply(this,arguments);
    setTimeout(function(){
      document.querySelectorAll('.reveal:not(.revealed),.reveal-scale:not(.revealed)').forEach(function(el){observer.observe(el)});
    },200);
  };
})();
// ═══ 3D TILT EFFECT ═══
(function(){
  document.querySelectorAll('.tilt-card').forEach(function(card){
    card.addEventListener('mousemove',function(e){
      var rect=card.getBoundingClientRect();
      var x=(e.clientX-rect.left)/rect.width-.5;
      var y=(e.clientY-rect.top)/rect.height-.5;
      card.style.transform='perspective(800px) rotateY('+(x*8)+'deg) rotateX('+(-y*6)+'deg)';
      var inner=card.querySelector('.tilt-inner');
      if(inner) inner.style.transform='translateZ(15px)';
    });
    card.addEventListener('mouseleave',function(){
      card.style.transform='perspective(800px) rotateY(0) rotateX(0)';
      var inner=card.querySelector('.tilt-inner');
      if(inner) inner.style.transform='translateZ(0)';
    });
  });
})();
