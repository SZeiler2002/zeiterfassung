document.querySelectorAll('[data-confirm]').forEach(b=>b.addEventListener('click',e=>{if(!confirm(b.dataset.confirm))e.preventDefault();}));
const form=document.querySelector('#entry-form');
if(form){
 const keys=['start','break_start','break_end','end'];
 const mins=s=>{const [h,m]=s.split(':').map(Number);return h*60+m;};
 const fmt=n=>`${n<0?'−':''}${Math.floor(Math.abs(n)/60)}:${String(Math.abs(n)%60).padStart(2,'0')}`;
 function update(){
  const times=keys.map(k=>document.querySelector('#id_'+k).value);
  const filled=times.filter(Boolean).map(mins);
  const out=document.querySelector('#live-total');
  if(filled.some((v,i)=>i>0&&v<=filled[i-1])){out.textContent='Bitte die Reihenfolge der Stempelzeiten prüfen.';return;}
  const partial=(!!times[0]!==!!times[1])||(!!times[2]!==!!times[3]);
  let work=0; for(const i of [0,2])if(times[i]&&times[i+1])work+=mins(times[i+1])-mins(times[i]);
  let target=Number(document.querySelector('#id_target_override').value||form.dataset.target);
  const kind=document.querySelector('#id_kind').value, fraction=Number(document.querySelector('#id_fraction').value);
  let credit=['vacation','holiday','sick'].includes(kind)?Math.round(target*fraction):0;
  if(kind==='unpaid')target-=Math.round(target*fraction);
  const delta=work+credit-target;
  out.textContent=`Arbeit ${fmt(work)} h · Gutschrift ${fmt(credit)} h · Vorschau Saldo ${delta>=0?'+':''}${fmt(delta)} h${partial?' · Stempelzeit fehlt':''}`;
 }
 form.addEventListener('input',update);update();
}
