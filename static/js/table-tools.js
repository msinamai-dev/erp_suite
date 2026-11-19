(function () {
  function enhance(table) {
    if (table.dataset.tableToolsReady || table.classList.contains('table-no-tools') || !table.tBodies.length) return;
    const body = table.tBodies[0];
    const allRows = Array.from(body.rows).filter(row => !row.querySelector('td[colspan]'));
    if (allRows.length < 1) return;
    table.dataset.tableToolsReady = '1';
    const parent = table.closest('.table-responsive') || table;
    const toolbar = document.createElement('div'); toolbar.className = 'table-tools';
    const searchWrap = document.createElement('label'); searchWrap.className = 'table-search';
    searchWrap.innerHTML = '<i class="bi bi-search"></i><input type="search" aria-label="Search this table" placeholder="Search this table…">';
    const right = document.createElement('div'); right.className = 'd-flex align-items-center gap-2 flex-wrap';
    const count = document.createElement('span'); count.className = 'table-count';
    const sizeLabel = document.createElement('label'); sizeLabel.className = 'd-flex align-items-center gap-2 small text-muted'; sizeLabel.append('Rows');
    const size = document.createElement('select'); size.setAttribute('aria-label','Rows per page');
    [10,15].forEach(n => { const opt = document.createElement('option'); opt.value = n; opt.textContent = n; if(n===15) opt.selected=true; size.appendChild(opt); });
    sizeLabel.appendChild(size); right.append(count,sizeLabel); toolbar.append(searchWrap,right);
    const pager = document.createElement('div'); pager.className = 'table-pagination';
    parent.parentNode.insertBefore(toolbar, parent); parent.parentNode.insertBefore(pager, parent.nextSibling);
    const input = searchWrap.querySelector('input'); let page=1;
    function draw(){
      const term=input.value.trim().toLocaleLowerCase();
      const filtered=allRows.filter(row => row.innerText.toLocaleLowerCase().includes(term));
      const pageSize=Number(size.value); const pages=Math.max(1,Math.ceil(filtered.length/pageSize)); page=Math.min(page,pages);
      allRows.forEach(row => row.style.display='none');
      filtered.slice((page-1)*pageSize,page*pageSize).forEach(row=>row.style.display='');
      count.textContent=filtered.length ? `${(page-1)*pageSize+1}–${Math.min(page*pageSize,filtered.length)} of ${filtered.length}` : '0 results';
      pager.replaceChildren();
      function btn(label,target,disabled,active){const b=document.createElement('button');b.type='button';b.textContent=label;b.disabled=disabled;if(active)b.classList.add('active');b.addEventListener('click',()=>{page=target;draw()});pager.appendChild(b)}
      btn('‹',Math.max(1,page-1),page===1,false);
      const start=Math.max(1,Math.min(page-2,pages-4)); const end=Math.min(pages,start+4);
      for(let n=start;n<=end;n++)btn(String(n),n,false,n===page);
      btn('›',Math.min(pages,page+1),page===pages,false);
    }
    input.addEventListener('input',()=>{page=1;draw()}); size.addEventListener('change',()=>{page=1;draw()}); draw();
  }
  document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('table').forEach(enhance);const observer=new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType!==1)return;if(node.matches&&node.matches('table'))enhance(node);if(node.closest){const parentTable=node.closest('table');if(parentTable)enhance(parentTable)}if(node.querySelectorAll)node.querySelectorAll('table').forEach(enhance)})));observer.observe(document.body,{childList:true,subtree:true});});
})();
