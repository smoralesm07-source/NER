let DATA = null;
const labels = {
  PERSONA_NATURAL:'Personas', PERSONA_JURIDICA:'Personas jurídicas', ORGANISMO_PUBLICO:'Organismos públicos',
  INSTITUCION_FINANCIERA:'Inst. financieras', LUGAR:'Lugares', PAIS:'Países', REGION:'Regiones', CIUDAD_COMUNA:'Ciudades/comunas'
};

async function loadData(){
  const r = await fetch(`data/latest.json?t=${Date.now()}`, {cache:'no-store'});
  DATA = await r.json();
  render();
}
function esc(v=''){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function render(){
  const a=DATA.article;
  document.querySelector('#title').textContent=a.title||'Noticia analizada';
  document.querySelector('#meta').textContent=[a.site_name,a.date,a.author].filter(Boolean).join(' · ');
  const link=document.querySelector('#sourceLink'); link.href=a.url||'#'; link.style.display=a.url?'inline-block':'none';
  document.querySelector('#articleText').textContent=a.text||'';
  const total=DATA.entities.length;
  const high=DATA.entities.filter(e=>e.confidence==='ALTA').length;
  const metrics=[['Entidades',total],['Alta confianza',high],['Personas',DATA.stats.PERSONA_NATURAL||0],['Jurídicas',DATA.stats.PERSONA_JURIDICA||0],['Organismos',DATA.stats.ORGANISMO_PUBLICO||0],['Lugares',(DATA.stats.LUGAR||0)+(DATA.stats.PAIS||0)+(DATA.stats.REGION||0)+(DATA.stats.CIUDAD_COMUNA||0)]];
  document.querySelector('#metrics').innerHTML=metrics.map(([l,v])=>`<div class="card metric"><b>${v}</b><span>${l}</span></div>`).join('');
  const types=[...new Set(DATA.entities.map(e=>e.type))].sort();
  document.querySelector('#typeFilter').innerHTML='<option value="">Todos los tipos</option>'+types.map(t=>`<option value="${esc(t)}">${esc(labels[t]||t)}</option>`).join('');
  renderEntities(); renderRelations();
}
function renderEntities(){
  const tf=document.querySelector('#typeFilter').value, cf=document.querySelector('#confidenceFilter').value;
  const items=DATA.entities.filter(e=>(!tf||e.type===tf)&&(!cf||e.confidence===cf));
  const box=document.querySelector('#entities');
  box.innerHTML=items.length?items.map((e,i)=>`<div class="entity" data-name="${esc(e.canonical_name)}">
    <div><div class="entity-name">${esc(e.canonical_name)}</div><div class="entity-sub">${esc(e.role||e.subtype||e.mention)}</div></div>
    <div><span class="type">${esc(labels[e.type]||e.type)}</span></div><div class="confidence ${e.confidence}">${e.confidence}</div></div>`).join(''):'<div class="empty">No hay entidades para este filtro.</div>';
  box.querySelectorAll('.entity').forEach(el=>el.addEventListener('click',()=>showDetail(items.find(e=>e.canonical_name===el.dataset.name))));
}
function showDetail(e){
  document.querySelector('#detail').innerHTML=`<div class="detail-title">${esc(e.canonical_name)}</div><span class="type">${esc(labels[e.type]||e.type)}</span>
  <dl class="kv"><dt>Mención</dt><dd>${esc(e.mention)}</dd><dt>Subtipo</dt><dd>${esc(e.subtype||'—')}</dd><dt>Rol</dt><dd>${esc(e.role||'—')}</dd><dt>Confianza</dt><dd>${esc(e.confidence)}</dd><dt>Aliases</dt><dd>${esc((e.aliases||[]).join(', ')||'—')}</dd><dt>Span</dt><dd>${e.start_char}–${e.end_char}</dd></dl>
  <div class="evidence">${esc(e.evidence||'Sin evidencia disponible')}</div><div class="signals">${(e.signals||[]).map(s=>`<span class="signal">${esc(s)}</span>`).join('')}</div>`;
}
function renderRelations(){
  const box=document.querySelector('#relations'); const rs=DATA.relations||[];
  box.innerHTML=rs.length?rs.map(r=>`<div class="relation"><b>${esc(r.source)}</b> → ${esc(r.relation)} → <b>${esc(r.target)}</b><div class="entity-sub">${esc(r.evidence||'')}</div></div>`).join(''):'<div class="empty">No se detectaron relaciones explícitas validadas.</div>';
}
document.querySelector('#refreshBtn').addEventListener('click',loadData);
document.querySelector('#typeFilter').addEventListener('change',renderEntities);
document.querySelector('#confidenceFilter').addEventListener('change',renderEntities);
loadData().catch(e=>{document.querySelector('#title').textContent='No se pudo cargar latest.json'; console.error(e);});

function githubRepo(){
  const host=window.location.hostname;
  if(!host.endsWith('.github.io')) return null;
  const owner=host.split('.')[0];
  const repo=window.location.pathname.split('/').filter(Boolean)[0];
  return repo?{owner,repo}:null;
}
document.querySelector('#analyzeBtn').addEventListener('click',()=>{
  const input=document.querySelector('#newsUrl'); const url=input.value.trim(); const note=document.querySelector('#formNote');
  try{ const u=new URL(url); if(!['http:','https:'].includes(u.protocol)) throw new Error(); }
  catch{ note.textContent='Ingresa una URL http/https válida.'; return; }
  const r=githubRepo();
  if(!r){ note.textContent='Esta función se habilita al publicar la app en GitHub Pages.'; return; }
  const title='[NER] Analizar noticia';
  const body=`URL: ${url}\n\nSolicitud generada desde GitHub Pages.`;
  const target=`https://github.com/${r.owner}/${r.repo}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  window.open(target,'_blank','noopener');
  note.textContent='GitHub abrirá la solicitud prellenada. Publícala para ejecutar el análisis.';
});
