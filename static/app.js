// ═══ UTILS ═══
// Utilitário Global de Comunicação
async function api(url, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) options.body = JSON.stringify(body);
  
  try {
    const res = await fetch(url, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.mensagem || 'Falha na comunicação com o Nexus');
    return data;
  } catch (err) {
    console.error('Nexus API Error:', err);
    throw err;
  }
}

// Formatação Monetária BRL
function fmt(val) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);
}

function showMsg(id,text,ok=true){
  const el=document.getElementById(id);
  if(!el)return;
  el.className='msg '+(ok?'msg-ok':'msg-err');
  el.textContent=text;el.style.display='block';
  setTimeout(()=>el.style.display='none',4000);
}

// ═══ NAV ═══
function navTo(section){
  document.querySelectorAll('.page-section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('sec-'+section)?.classList.add('active');
  document.querySelectorAll(`[data-sec="${section}"]`).forEach(n=>n.classList.add('active'));
  const loaders={'dashboard':loadDashboard,'estoque':loadEstoque,'pedidos':loadPedidos,
    'vendedores':loadVendedores,'reunioes':loadReunioes,'historico':loadHistorico,
    'contatos':loadContatos,'categorias':loadCategorias};
  if(loaders[section])loaders[section]();
}

// ═══ LOGOUT ═══
async function logout(){
  await fetch('/api/logout',{method:'POST'});
  location.href='/';
}

// ═══ DASHBOARD ═══
async function loadDashboard(){
  try{
    const d=await api('/api/dashboard');
    const update=(id,val)=>{let el=document.getElementById(id); if(el) el.textContent=val;};
    update('d-produtos', d.total_produtos);
    update('d-valor', fmt(d.valor_total));
    update('d-baixos', d.produtos_baixos);
    update('d-sem', d.sem_estoque);
    update('d-pedidos', d.total_pedidos);
    update('d-vpedidos', fmt(d.valor_pedidos));
    update('d-vendedores', d.total_vendedores);
    update('d-reunioes', d.reunioes_pendentes);
  }catch(e){console.error(e)}
}

// ═══ CATEGORIAS ═══
async function loadCategorias(){
  try{
    const cats=await api('/api/categorias');
    const tb=document.getElementById('tb-categorias');
    tb.innerHTML=cats.length?'':'<tr><td colspan="3" class="empty-state">Nenhuma categoria</td></tr>';
    cats.forEach(c=>{
      tb.innerHTML+=`<tr><td>${c.id}</td><td>${c.nome}</td>
        <td><button class="btn btn-danger btn-sm" onclick="delCategoria(${c.id})"><i class="fas fa-trash"></i></button></td></tr>`;
    });
  }catch(e){console.error(e)}
}
async function addCategoria(){
  const inp=document.getElementById('inp-cat');
  const nome=inp.value.trim();
  if(!nome)return alert('Digite o nome');
  try{await api('/api/categorias',{method:'POST',body:JSON.stringify({nome})});inp.value='';loadCategorias();showMsg('msg-cat','Categoria criada!');}
  catch(e){showMsg('msg-cat',e.message,false)}
}
async function delCategoria(id){
  if(!confirm('Deletar?'))return;
  await api(`/api/categorias/${id}`,{method:'DELETE'});loadCategorias();
}

// ═══ PRODUTOS / ESTOQUE ═══
let produtosCache=[];
async function loadEstoque(){
  try{
    produtosCache=await api('/api/produtos');
    renderEstoque();
    await loadCatSelect();
  }catch(e){console.error(e)}
}
function renderEstoque(filter=''){
  const q=filter.toLowerCase();
  const list=produtosCache.filter(p=>!q||p.nome.toLowerCase().includes(q)||(p.sku||'').toLowerCase().includes(q)||(p.categoria_nome||'').toLowerCase().includes(q));
  const tb=document.getElementById('tb-estoque');
  tb.innerHTML=list.length?'':'<tr><td colspan="10" class="empty-state">Nenhum produto</td></tr>';
  list.forEach(p=>{
    const st=p.quantidade===0?'<span class="badge badge-danger">ESGOTADO</span>':p.quantidade<=p.minimo?'<span class="badge badge-amber">ESTOQUE BAIXO</span>':'<span class="badge badge-ok">DISPONÍVEL</span>';
    const lucro=p.preco-(p.custo||0);
    tb.innerHTML+=`<tr>
      <td><span style="color:var(--muted); font-weight:700;">#${p.id}</span></td>
      <td><div style="font-weight:700;">${p.nome}</div><div style="font-size:0.7rem; color:var(--muted);">SKU: ${p.sku||'-'}</div></td>
      <td><span class="badge badge-info">${p.categoria_nome||'Geral'}</span></td>
      <td>${fmt(p.custo||0)}</td>
      <td><span style="font-weight:700;">${fmt(p.preco)}</span></td>
      <td><strong style="color:var(--green)">+${fmt(lucro)}</strong></td>
      <td><strong style="font-size:1.1rem;">${p.quantidade}</strong></td>
      <td>${st}</td>
      <td>
        <div style="display:flex; gap:5px;">
          <button class="btn btn-primary btn-sm" style="padding:6px 10px;" onclick="promptEntrada(${p.id})" title="Adicionar estoque"><i class="fas fa-plus"></i></button>
          <button class="btn btn-outline btn-sm" style="padding:6px 10px; color:var(--red);" onclick="delProduto(${p.id})"><i class="fas fa-trash-can"></i></button>
        </div>
      </td></tr>`;
  });
}
async function loadCatSelect(){
  const cats=await api('/api/categorias');
  const sel=document.getElementById('sel-cat-prod');
  if(!sel)return;
  sel.innerHTML='<option value="">-- Categoria --</option>';
  cats.forEach(c=>sel.innerHTML+=`<option value="${c.id}">${c.nome}</option>`);
}
async function addProduto(e){
  e.preventDefault();
  const f=e.target;
  const catNome=document.getElementById('new-cat-prod').value.trim();
  const fd = new FormData(f);
  if(catNome) fd.append('categoria_nome', catNome);
  
  try{
    const r=await fetch('/api/produtos',{method:'POST',body:fd});
    const j=await r.json();
    if(!r.ok) throw new Error(j.mensagem||'Erro ao criar produto');
    f.reset();document.getElementById('new-cat-prod').value='';
    showMsg('msg-prod','Produto cadastrado!');loadEstoque();
  }catch(e){showMsg('msg-prod',e.message,false)}
}
async function promptEntrada(id){
  const qtd=prompt('Quantidade para adicionar:');
  if(!qtd||isNaN(qtd)||+qtd<=0)return;
  try{await api(`/api/produtos/${id}/entrada`,{method:'POST',body:JSON.stringify({quantidade:+qtd})});loadEstoque();showMsg('msg-prod','Estoque atualizado!');}
  catch(e){alert(e.message)}
}
async function delProduto(id){
  if(!confirm('Deletar produto?'))return;
  await api(`/api/produtos/${id}`,{method:'DELETE'});loadEstoque();
}

// ═══ VENDEDORES ═══
async function loadVendedores(){
  try{
    const vs=await api('/api/vendedores');
    const tb=document.getElementById('tb-vendedores');
    tb.innerHTML=vs.length?'':'<tr><td colspan="6" class="empty-state">Nenhum vendedor</td></tr>';
    vs.forEach(v=>{
      tb.innerHTML+=`<tr><td>${v.id}</td><td>${v.nome}</td><td>${v.email||'-'}</td>
        <td>${v.telefone||'-'}</td><td>${v.comissao}%</td>
        <td><button class="btn btn-danger btn-sm" onclick="delVendedor(${v.id})"><i class="fas fa-trash"></i></button></td></tr>`;
    });
  }catch(e){console.error(e)}
}
async function addVendedor(e){
  e.preventDefault();
  const f=e.target;
  const data={nome:f.nome.value,email:f.email.value,telefone:f.telefone.value,comissao:f.comissao.value||0};
  try{await api('/api/vendedores',{method:'POST',body:JSON.stringify(data)});f.reset();showMsg('msg-vend','Vendedor cadastrado!');loadVendedores();}
  catch(e){showMsg('msg-vend',e.message,false)}
}
async function delVendedor(id){
  if(!confirm('Deletar?'))return;
  await api(`/api/vendedores/${id}`,{method:'DELETE'});loadVendedores();
}

// ═══ PEDIDOS ═══
let itensPedido=[];
async function loadPedidos(){
  try{
    const ps=await api('/api/pedidos');
    const tb=document.getElementById('tb-pedidos');
    tb.innerHTML=ps.length?'':'<tr><td colspan="7" class="empty-state">Nenhum pedido</td></tr>';
    ps.forEach(p=>{
      let badgeClass = 'badge-info';
      let statusLabel = p.status.toUpperCase();
      if(p.status === 'concluido') { badgeClass = 'badge-ok'; statusLabel = 'CONCLUÍDO'; }
      if(p.status === 'cancelado') { badgeClass = 'badge-danger'; statusLabel = 'CANCELADO'; }
      if(p.status === 'pendente') { badgeClass = 'badge-amber'; statusLabel = 'PROCESSANDO'; }

      tb.innerHTML+=`<tr>
        <td><span style="font-weight:800; color:var(--accent);">#${p.id}</span></td>
        <td><div style="font-weight:700;">${p.cliente_nome}</div><div style="font-size:0.7rem; color:var(--muted);">${p.fornecedor_nome ? 'Fornecedor: '+p.fornecedor_nome : ''}</div></td>
        <td>${p.data}</td>
        <td><span style="font-weight:600;">${p.quantidade_itens} itens</span></td>
        <td><span style="font-size:1.1rem; font-weight:800; color:var(--green);">${fmt(p.total)}</span></td>
        <td><span class="badge ${badgeClass}">${statusLabel}</span></td>
        <td>
          <div style="display:flex; gap:5px;">
            <button class="btn btn-outline btn-sm" style="color:var(--green); border-color:rgba(16,185,129,0.2);" onclick="setStatusPedido(${p.id},'concluido')" title="Concluir"><i class="fas fa-check"></i></button>
            <button class="btn btn-outline btn-sm" style="color:var(--red); border-color:rgba(239,68,68,0.2);" onclick="setStatusPedido(${p.id},'cancelado')" title="Cancelar"><i class="fas fa-xmark"></i></button>
          </div>
        </td></tr>`;
    });
    // Load products for order form
    const prods=await api('/api/produtos');
    const sel=document.getElementById('sel-prod-pedido');
    if(sel){sel.innerHTML='<option value="">-- Produto --</option>';
      prods.filter(p=>p.quantidade>0).forEach(p=>sel.innerHTML+=`<option value="${p.id}" data-nome="${p.nome}" data-preco="${p.preco}">${p.nome} (${p.quantidade} disp.)</option>`);}
    const vends=await api('/api/vendedores');
    const selV=document.getElementById('sel-vend-pedido');
    if(selV){selV.innerHTML='<option value="">-- Vendedor (opc.) --</option>';
      vends.forEach(v=>selV.innerHTML+=`<option value="${v.id}">${v.nome}</option>`);}
  }catch(e){console.error(e)}
}
function addItemPedido(){
  const sel=document.getElementById('sel-prod-pedido');
  const opt=sel.selectedOptions[0];if(!opt||!opt.value)return alert('Selecione um produto');
  const qtd=parseInt(document.getElementById('qtd-pedido').value)||1;
  const preco=parseFloat(opt.dataset.preco);
  itensPedido.push({produto_id:+opt.value,nome:opt.dataset.nome,quantidade:qtd,preco,subtotal:preco*qtd});
  renderItensPedido();
}
function renderItensPedido(){
  const tb=document.getElementById('tb-itens-pedido');
  tb.innerHTML='';let total=0;
  itensPedido.forEach((it,i)=>{
    total+=it.subtotal;
    tb.innerHTML+=`<tr><td>${it.nome}</td><td>${it.quantidade}</td><td>${fmt(it.preco)}</td><td>${fmt(it.subtotal)}</td>
      <td><button class="btn btn-danger btn-sm" onclick="itensPedido.splice(${i},1);renderItensPedido()"><i class="fas fa-times"></i></button></td></tr>`;
  });
  document.getElementById('total-pedido').textContent=fmt(total);
}
async function criarPedido(e){
  e.preventDefault();if(!itensPedido.length)return alert('Adicione itens');
  const f=e.target;
  const data={cliente_nome:f.cliente.value,data:f.data_pedido.value,vendedor_id:f.vendedor_id.value||null,observacoes:f.observacoes.value,itens:itensPedido};
  try{await api('/api/pedidos',{method:'POST',body:JSON.stringify(data)});
    f.reset();itensPedido=[];renderItensPedido();showMsg('msg-pedido','Pedido criado!');loadPedidos();
  }catch(e){showMsg('msg-pedido',e.message,false)}
}
async function setStatusPedido(id,status){
  await api(`/api/pedidos/${id}/status`,{method:'PUT',body:JSON.stringify({status})});loadPedidos();
}

// ═══ REUNIÕES ═══
async function loadReunioes(){
  try{
    const rs=await api('/api/reunioes');
    const tb=document.getElementById('tb-reunioes');
    tb.innerHTML=rs.length?'':'<tr><td colspan="6" class="empty-state">Nenhuma reunião</td></tr>';
    rs.forEach(r=>{
      const badge=r.status==='concluida'?'badge-ok':r.status==='cancelada'?'badge-danger':'badge-info';
      tb.innerHTML+=`<tr><td>${r.titulo}</td><td>${r.data_hora}</td><td>${r.local||'-'}</td>
        <td>${r.participantes||'-'}</td><td><span class="badge ${badge}">${r.status}</span></td>
        <td>
          <button class="btn btn-sm btn-outline" onclick="setStatusReuniao(${r.id},'concluida')">✓</button>
          <button class="btn btn-sm btn-danger" onclick="delReuniao(${r.id})"><i class="fas fa-trash"></i></button>
        </td></tr>`;
    });
  }catch(e){console.error(e)}
}
async function addReuniao(e){
  e.preventDefault();const f=e.target;
  const data={titulo:f.titulo.value,descricao:f.descricao.value,data_hora:f.data_hora.value,local:f.local.value,participantes:f.participantes.value};
  try{await api('/api/reunioes',{method:'POST',body:JSON.stringify(data)});f.reset();showMsg('msg-reuniao','Reunião agendada!');loadReunioes();}
  catch(e){showMsg('msg-reuniao',e.message,false)}
}
async function setStatusReuniao(id,st){await api(`/api/reunioes/${id}/status`,{method:'PUT',body:JSON.stringify({status:st})});loadReunioes();}
async function delReuniao(id){if(!confirm('Deletar?'))return;await api(`/api/reunioes/${id}`,{method:'DELETE'});loadReunioes();}

// ═══ CONTATOS ═══
async function loadContatos(){
  try{
    const cs=await api('/api/contatos');
    const tb=document.getElementById('tb-contatos');
    tb.innerHTML=cs.length?'':'<tr><td colspan="6" class="empty-state">Nenhum contato</td></tr>';
    cs.forEach(c=>{
      tb.innerHTML+=`<tr><td>${c.nome}</td><td>${c.documento||'-'}</td><td>${c.email||'-'}</td>
        <td>${c.telefone||'-'}</td><td>${c.tipo}</td>
        <td><button class="btn btn-danger btn-sm" onclick="delContato(${c.id})"><i class="fas fa-trash"></i></button></td></tr>`;
    });
  }catch(e){console.error(e)}
}
async function addContato(e){
  e.preventDefault();const f=e.target;
  const data={nome:f.nome.value,documento:f.documento.value,email:f.email.value,telefone:f.telefone.value,endereco:f.endereco.value,tipo:f.tipo.value};
  try{await api('/api/contatos',{method:'POST',body:JSON.stringify(data)});f.reset();showMsg('msg-contato','Contato adicionado!');loadContatos();}
  catch(e){showMsg('msg-contato',e.message,false)}
}
async function delContato(id){if(!confirm('Deletar?'))return;await api(`/api/contatos/${id}`,{method:'DELETE'});loadContatos();}

// ═══ HISTÓRICO ═══
async function loadHistorico(){
  try{
    const tipo=document.getElementById('filtro-tipo')?.value||'';
    const di=document.getElementById('filtro-di')?.value||'';
    const df=document.getElementById('filtro-df')?.value||'';
    let url='/api/historico?';
    if(tipo)url+=`tipo=${tipo}&`;if(di)url+=`data_inicio=${di}&`;if(df)url+=`data_fim=${df}&`;
    const hs=await api(url);
    const tb=document.getElementById('tb-historico');
    tb.innerHTML=hs.length?'':'<tr><td colspan="5" class="empty-state">Nenhum registro</td></tr>';
    hs.forEach(h=>{
      const badge=h.tipo==='entrada'?'badge-ok':'badge-danger';
      tb.innerHTML+=`<tr><td>${h.produto_nome}</td><td><span class="badge ${badge}">${h.tipo}</span></td>
        <td>${h.quantidade}</td><td>${h.data_hora}</td><td>${h.observacoes||'-'}</td></tr>`;
    });
  }catch(e){console.error(e)}
}

// ═══ INIT ═══
document.addEventListener('DOMContentLoaded',()=>{navTo('dashboard');});
