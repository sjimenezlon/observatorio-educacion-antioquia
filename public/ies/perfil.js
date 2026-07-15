(() => {
  'use strict';

  const iesId = document.body.dataset.ies;
  const app = document.getElementById('app');
  const pages = {itm:'itm.html', pascual:'pascual-bravo.html', colmayor:'colmayor.html'};
  const colors = {itm:'#78aef5', pascual:'#ffd087', colmayor:'#78e3c3'};
  const narratives = {
    itm: {
      official:'https://www.itm.edu.co/',
      thesis:'La escala tecnológica del sistema público de Medellín',
      intro:'El ITM concentra la mayor matrícula de las tres IES y articula tecnologías, ingenierías, ciencias, artes y posgrados. Su pregunta estratégica no es solo cómo crecer, sino cómo convertir esa escala en trayectorias completas y resultados verificables.',
      questions:[
        ['Portafolio','¿Dónde construir rutas tecnología → profesional → posgrado?','Identificar homologaciones, tiempos reales y continuidad entre ciclos evitaría que la amplitud del catálogo funcione como programas aislados.','Indicador: estudiantes que continúan por ruta articulada'],
        ['Calidad','¿Qué programas de mayor matrícula deben priorizar acreditación?','La escala hace que una decisión de calidad pueda afectar a miles de estudiantes. Conviene cruzar matrícula, vigencia del registro y resultados de aprendizaje.','Indicador: matrícula cubierta por acreditación vigente'],
        ['Territorio','¿Qué parte de la expansión genera permanencia y graduación?','La presencia fuera del campus principal debe medirse por cohortes, continuidad y resultados, no solamente por matrículas o convenios abiertos.','Indicador: retención y graduación por sede o convenio']
      ]
    },
    pascual: {
      official:'https://pascualbravo.edu.co/',
      thesis:'La conexión pública entre industria, diseño y transformación digital',
      intro:'Pascual Bravo ocupa una posición singular entre formación tecnológica, ingeniería, diseño y producción. Su alcance reportado en 47 municipios abre una oportunidad para medir qué modelos de regionalización producen trayectorias sostenibles.',
      questions:[
        ['Articulación','¿Qué programas pueden compartir rutas con ITM?','Las proximidades en software, energía, electromecánica y gestión permiten explorar homologaciones y especializaciones complementarias, sin duplicar innecesariamente capacidad pública.','Indicador: créditos homologables y demanda no atendida'],
        ['Regionalización','¿En cuáles municipios la presencia se convierte en graduación?','El alcance territorial debe distinguir convenio, cohorte activa, matrícula, permanencia y graduados para saber dónde el modelo es sostenible.','Indicador: cohortes activas y graduación por municipio'],
        ['Calidad','¿Cómo ampliar la cobertura de acreditación sin frenar el acceso?','La prioridad puede ordenarse por matrícula, madurez del programa, resultados y relevancia productiva, declarando siempre el denominador.','Indicador: matrícula acreditada por campo de formación']
      ]
    },
    colmayor: {
      official:'https://www.colmayor.edu.co/',
      thesis:'La especialización pública en salud, hábitat y territorio',
      intro:'Colmayor complementa el sistema con una oferta diferenciada en salud, construcción, ambiente, turismo, gastronomía y desarrollo social. Su valor estratégico está en conectar especialización académica con problemas concretos de ciudad y región.',
      questions:[
        ['Especialización','¿Qué capacidades distintivas deben escalarse como sistema?','Salud, hábitat, catastro, ambiente y turismo pueden convertirse en nodos compartidos para prácticas, investigación aplicada y educación continua del Distrito.','Indicador: proyectos y prácticas con resultado territorial'],
        ['Sostenibilidad','¿Qué crecimiento depende de recursos permanentes?','La lectura financiera debe separar transferencias estables, gratuidad, recursos propios y convenios para anticipar riesgos de liquidez y expansión.','Indicador: ingreso recurrente por estudiante'],
        ['Cobertura','¿Qué oferta virtual reduce brechas sin perder permanencia?','La modalidad puede ampliar acceso, pero debe observarse junto con ingreso, actividad académica, retención y graduación de cada cohorte.','Indicador: permanencia comparable por modalidad']
      ]
    }
  };

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const fmt = value => Number(value || 0).toLocaleString('es-CO');
  const pct = value => Number(value || 0).toLocaleString('es-CO',{maximumFractionDigits:1}) + ' %';
  const money = value => '$' + Number(value || 0).toLocaleString('es-CO',{maximumFractionDigits:0}) + ' M';
  const signedMoney = value => (Number(value) >= 0 ? '+$' : '−$') + Math.abs(Number(value || 0)).toLocaleString('es-CO',{maximumFractionDigits:0}) + ' M';
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const safeUrl = value => String(value || '').startsWith('https://') ? esc(value) : '#';

  function bars(values, total, limit = 8) {
    const rows = Object.entries(values || {}).sort((a,b) => b[1] - a[1]).slice(0, limit);
    const max = Math.max(...rows.map(([,value]) => value), 1);
    return `<div class="bars">${rows.map(([label,value]) => `<div class="bar-row"><label title="${esc(label)}">${esc(label)}</label><div class="bar"><span style="width:${100*value/max}%"></span></div><b>${fmt(value)} · ${pct(100*value/total)}</b></div>`).join('')}</div>`;
  }

  function nav(current, institutions) {
    return `<nav class="topbar"><div class="shell topbar-inner"><a class="brand" href="../index.html">Mater<span>IA</span> Gris</a><div class="profile-nav" aria-label="Perfiles de las IES">${institutions.map(item => `<a href="${pages[item.id]}" ${item.id===current?'aria-current="page"':''}>${esc(item.nombre_corto)}</a>`).join('')}</div><a class="back-link" href="../index.html#distrito">← <span>Volver al sistema distrital</span></a></div></nav>`;
  }

  function render(data) {
    const institution = data.instituciones.find(item => item.id === iesId);
    if (!institution || !narratives[iesId]) throw new Error('IES no encontrada');
    const n = narratives[iesId];
    const snies = institution.snies_2024;
    const signal = institution.distrito_2026_02_28;
    const finance = institution.finanzas;
    const programs = data.programas_snies_2024.filter(item => item.ies_id === iesId);
    const share = 100 * institution.matricula_2026_1 / data.sistema.matricula_2026_1;
    const delta = institution.matricula_2026_1 - institution.matricula_2025_2;
    const deltaPct = 100 * delta / institution.matricula_2025_2;
    const districtSource = data.fuentes.find(item => item.nombre.includes('Plan Indicativo'))?.url || '#';
    const accreditedShare = snies.matricula ? 100 * snies.matricula_acreditada / snies.matricula : 0;
    const announcedPrefix = institution.programas_calificador === 'cerca de' ? '≈' : '';
    const cupsPrefix = institution.cupos_calificador === 'más de' ? '>' : '';
    const partial = finance.corte_resultado !== '2025-12-31';

    app.innerHTML = `${nav(iesId,data.instituciones)}
      <header class="hero"><div class="shell hero-grid"><div><span class="eyebrow">Perfil institucional · sistema público de Medellín</span><h1>${esc(institution.nombre_corto)}</h1><p class="hero-copy"><b style="color:var(--ink)">${esc(n.thesis)}.</b> ${esc(n.intro)}</p><div class="cut"><span>Matrícula distrital · 2026-1</span><span>Oferta comparable · SNIES 2024</span><span>Catálogo web · ${esc(institution.catalogo_web.consultado)}</span><span>Finanzas · cortes declarados</span></div><a class="official-site" href="${safeUrl(n.official)}" target="_blank" rel="noopener">Visitar sitio oficial de ${esc(institution.nombre_corto)} ↗</a></div><aside class="share-card"><small>Participación en la matrícula de las tres IES</small><strong class="share-value">${pct(share)}</strong><p>${fmt(institution.matricula_2026_1)} de ${fmt(data.sistema.matricula_2026_1)} estudiantes en el corte oficial del 28 de febrero de 2026.</p><div class="share-track" aria-hidden="true"><span style="width:${share}%"></span></div></aside></div></header>
      <main id="contenido" class="shell">
        <section class="kpis" aria-label="Cifras principales"><article class="kpi"><small>Matrícula 2026-1</small><strong>${fmt(institution.matricula_2026_1)}</strong><span>Corte consolidado del Distrito · 28 feb.</span></article><article class="kpi"><small>Convocatoria 2026-2</small><strong>${announcedPrefix}${fmt(institution.programas_convocatoria_2026_2)}</strong><span>programas anunciados · ${cupsPrefix}${fmt(institution.cupos_2026_2)} cupos</span></article><article class="kpi"><small>Inventario SNIES 2024</small><strong>${fmt(snies.registros)}</strong><span>${fmt(snies.pregrado)} pregrados · ${fmt(snies.posgrado)} posgrados</span></article><article class="kpi"><small>Presupuesto 2026</small><strong>${money(finance.presupuesto_2026_millones)}</strong><span>Presupuesto aprobado, millones de pesos</span></article></section>
        <section class="official-pulse" aria-label="Indicadores oficiales 2026"><div class="pulse-head"><div><small>Seguimiento Plan Indicativo · 28 feb. 2026</small><h2>La señal institucional más reciente</h2></div><div class="pulse-delta"><b>${delta>=0?'+':''}${fmt(delta)} · ${deltaPct>=0?'+':''}${pct(deltaPct)}</b><span>variación frente a 2025-2 · comparación semestral</span></div></div><div class="pulse-grid"><article class="pulse-stat"><strong>${fmt(signal.programas_acreditados_vigentes)}</strong><span>programas acreditados vigentes</span></article><article class="pulse-stat"><strong>${fmt(signal.grupos_investigacion_a1_a_b)}</strong><span>grupos de investigación A1, A o B</span></article><article class="pulse-stat"><strong>${fmt(signal.programas_media_tecnica)}</strong><span>programas articulados con media técnica</span></article><article class="pulse-stat"><strong>${fmt(signal.programas_ftdh)}</strong><span>programas de formación para el trabajo</span></article><article class="pulse-stat"><strong>${fmt(signal.programas_comunas_corregimientos)}</strong><span>ofertas pertinentes en comunas/corregimientos</span></article><article class="pulse-stat"><strong>${fmt(signal.semilleros_activos)}</strong><span>semilleros de investigación activos</span></article><article class="pulse-stat"><strong>${fmt(signal.estudiantes_semilleros)}</strong><span>estudiantes vinculados a semilleros</span></article><article class="pulse-stat"><strong>${fmt(signal.publicaciones_indexadas)}</strong><span>publicaciones indexadas al corte</span></article></div><div class="pulse-source"><p>La variación usa el semestre inmediatamente anterior y puede contener estacionalidad. Los programas acreditados de este reporte no se igualan a los registros SNIES 2024.</p><a href="${safeUrl(districtSource)}" target="_blank" rel="noopener">Abrir reporte oficial ↗</a></div></section>

        <section class="section" id="oferta"><div class="section-head"><span class="section-no">01</span><div><h2>Una oferta con composición propia</h2><p>La convocatoria muestra lo disponible ahora; el catálogo web, las páginas visibles; y SNIES permite comparar con una definición común. Las tres capas se muestran sin igualarlas.</p></div></div><div class="grid">
          <article class="card half"><h3>Registros por nivel</h3><p class="card-note">SNIES 2024 · participación dentro de los ${fmt(snies.registros)} registros de la IES</p>${bars(snies.niveles,snies.registros)}</article>
          <article class="card half"><h3>Matrícula en programas acreditados</h3><p class="card-note">La acreditación se pondera por matrícula, no por un promedio simple de programas.</p><div class="gauge-wrap"><div class="gauge" style="--value:${accreditedShare}"><b>${pct(accreditedShare)}</b></div><div class="gauge-copy"><strong>${fmt(snies.matricula_acreditada)} estudiantes</strong><p>de ${fmt(snies.matricula)} registrados en el inventario comparable 2024. ${fmt(snies.acreditados)} de ${fmt(snies.registros)} registros aparecen acreditados.</p></div></div></article>
          <article class="card half"><h3>Modalidades</h3><p class="card-note">Conteo de registros, no matrícula ni cupos.</p>${bars(snies.modalidades,snies.registros)}</article>
          <article class="card half"><h3>Campos de conocimiento</h3><p class="card-note">Las áreas describen el portafolio regulado y no sustituyen un análisis de pertinencia.</p>${bars(snies.areas,snies.registros,7)}</article>
          <article class="card explorer"><h3>Explorar los programas comparables</h3><p class="card-note">Busque por nombre o área y filtre el mismo corte SNIES usado en el capítulo distrital.</p><div class="filters"><input id="program-q" type="search" placeholder="Buscar programa o área…" aria-label="Buscar programa"><select id="program-level" aria-label="Filtrar por nivel"><option value="">Todos los niveles</option>${[...new Set(programs.map(p=>p.nivel))].sort().map(v=>`<option>${esc(v)}</option>`).join('')}</select><select id="program-mode" aria-label="Filtrar por modalidad"><option value="">Todas las modalidades</option>${[...new Set(programs.map(p=>p.modalidad))].sort().map(v=>`<option>${esc(v)}</option>`).join('')}</select></div><div class="result-meta"><b id="program-count"></b><span>Orden inicial: matrícula 2024-II</span></div><div class="table-wrap" id="program-table"></div></article>
          <article class="card"><h3>Catálogo institucional visible</h3><p class="card-note">${fmt(institution.catalogo_web.registros_visibles)} entradas capturadas el ${esc(institution.catalogo_web.consultado)}. Una entrada puede representar una modalidad y no implica que tenga cupo abierto.</p><div class="catalog-list" id="catalog-list"></div><button class="catalog-toggle" id="catalog-toggle" type="button"></button></article>
        </div></section>

        <section class="section" id="finanzas"><div class="section-head"><span class="section-no">02</span><div><h2>Capacidad financiera, con magnitudes separadas</h2><p>Presupuesto, recaudo y resultado contable responden preguntas distintas. Activo, pasivo y patrimonio provienen del estado de situación financiera.</p></div></div><article class="card"><div class="finance-grid"><div class="finance-stat"><small>Presupuesto 2026</small><strong>${money(finance.presupuesto_2026_millones)}</strong><span>Autorización inicial/aprobada</span></div><div class="finance-stat"><small>Recaudo 2025</small><strong>${money(finance.recaudo_2025_millones)}</strong><span>Flujo presupuestal observado</span></div><div class="finance-stat"><small>Recursos del Estado</small><strong>${pct(finance.recursos_estado_pct)}</strong><span>${esc(finance.dependencia_real_nota || 'Participación documentada en el corte')}</span></div><div class="finance-stat"><small>Deuda financiera</small><strong>${money(finance.deuda_financiera_millones)}</strong><span>Según estados y notas revisadas</span></div><div class="finance-stat"><small>Activo</small><strong>${money(finance.activo_millones)}</strong><span>Estado de situación financiera</span></div><div class="finance-stat"><small>Pasivo</small><strong>${money(finance.pasivo_millones)}</strong><span>Obligaciones registradas</span></div><div class="finance-stat"><small>Patrimonio</small><strong>${money(finance.patrimonio_millones)}</strong><span>Activo menos pasivo</span></div><div class="finance-stat"><small>Resultado contable</small><strong style="color:var(--green)">${signedMoney(finance.resultado_contable_millones)}${partial?' *':''}</strong><span>${partial?'Corte marzo de 2026*':'Cierre diciembre de 2025'}</span></div></div><div class="finance-note"><span>◇</span><p><b>Regla de lectura:</b> ${partial?'el resultado de Pascual Bravo corresponde al primer trimestre de 2026 y no se compara como si fuera un año completo. ':''}La ecuación contable cierra dentro del redondeo publicado. Presupuesto, recaudo y resultado no se restan entre sí.</p></div><div class="source-row"><a href="${safeUrl(finance.fuente_presupuesto_2026)}" target="_blank" rel="noopener">Presupuesto 2026 ↗</a><a href="${safeUrl(finance.fuente_ejecucion_2025)}" target="_blank" rel="noopener">Ejecución 2025 ↗</a><a href="${safeUrl(finance.fuente_eeff)}" target="_blank" rel="noopener">Estados financieros ↗</a></div></article></section>

        <section class="section" id="decisiones"><div class="section-head"><span class="section-no">03</span><div><h2>Las preguntas que esta IES abre para Medellín</h2><p>No son calificaciones automáticas: son una agenda para convertir datos institucionales en decisiones de sistema.</p></div></div><div class="questions">${n.questions.map(([tag,title,copy,indicator])=>`<article class="question"><small>${esc(tag)}</small><h3>${esc(title)}</h3><p>${esc(copy)}</p><span>${esc(indicator)}</span></article>`).join('')}</div></section>

        <section class="section" id="sistema"><div class="section-head"><span class="section-no">3 → 1</span><div><h2>Comparar sin perder la complementariedad</h2><p>Cada perfil tiene un rol distinto. La pregunta de política pública es cómo coordinarlos como un portafolio común.</p></div></div><div class="institution-switch">${data.instituciones.map(item=>`<a href="${pages[item.id]}" class="${item.id===iesId?'active':''}" style="--switch:${colors[item.id]}"><small>${item.id===iesId?'Perfil actual':'Abrir perfil'}</small><strong>${esc(item.nombre_corto)}</strong></a>`).join('')}</div><div class="method"><p><b style="color:var(--ink-2)">Metodología:</b> corte oficial distrital al 28 de febrero de 2026, convocatoria 2026-2, catálogo web al ${esc(data.meta.corte)}, SNIES consolidado 2024 y estados financieros oficiales. Los cortes y definiciones no se mezclan; las limitaciones viajan en el archivo público.</p><a href="../ies-distritales.json" target="_blank" rel="noopener">Abrir datos y fuentes ↗</a></div></section>
      </main>
      <footer><div class="shell footer-inner"><span><b>MaterIA Gris</b> · El cerebro de datos de la educación superior de Antioquia</span><span>Perfil ${esc(institution.nombre_corto)} · corte ${esc(data.meta.corte)}</span></div></footer>`;

    const q = document.getElementById('program-q');
    const level = document.getElementById('program-level');
    const mode = document.getElementById('program-mode');
    const table = document.getElementById('program-table');
    const count = document.getElementById('program-count');
    const renderPrograms = () => {
      const term = normalize(q.value);
      const rows = programs.filter(p => (!level.value || p.nivel === level.value) && (!mode.value || p.modalidad === mode.value) && (!term || normalize(`${p.programa} ${p.area}`).includes(term)));
      count.textContent = `${fmt(rows.length)} registros · ${fmt(rows.reduce((sum,p)=>sum+Number(p.matricula24||0),0))} estudiantes`;
      table.innerHTML = rows.length ? `<table><thead><tr><th>Programa</th><th>Nivel</th><th>Modalidad</th><th>Área</th><th>Calidad</th><th class="num">Matrícula</th><th class="num">SNIES</th></tr></thead><tbody>${rows.map(p=>`<tr><td><span class="program-name">${esc(p.programa)}</span></td><td>${esc(p.nivel)}</td><td>${esc(p.modalidad)}</td><td>${esc(p.area)}</td><td>${p.acreditado?'<span class="quality">Acreditado</span>':'—'}</td><td class="num">${fmt(p.matricula24)}</td><td class="num">${fmt(p.snies)}</td></tr>`).join('')}</tbody></table>` : '<p style="padding:26px;color:var(--muted);font-size:10px;text-align:center">No hay registros que coincidan con estos filtros.</p>';
    };
    [level,mode].forEach(el => el.addEventListener('change',renderPrograms));
    q.addEventListener('input',renderPrograms);
    renderPrograms();

    const catalog = institution.catalogo_web.programas;
    const catalogHost = document.getElementById('catalog-list');
    const toggle = document.getElementById('catalog-toggle');
    let expanded = false;
    const renderCatalog = () => {
      const visible = expanded ? catalog : catalog.slice(0,12);
      catalogHost.innerHTML = visible.map(item=>`<a href="${safeUrl(item.fuente)}" target="_blank" rel="noopener"><span>${esc(item.programa)}<br><small style="color:var(--muted)">${esc(item.nivel)}</small></span><i>↗</i></a>`).join('');
      toggle.hidden = catalog.length <= 12;
      toggle.textContent = expanded ? 'Mostrar menos' : `Ver las ${fmt(catalog.length)} entradas del catálogo`;
      toggle.setAttribute('aria-expanded',String(expanded));
    };
    toggle.addEventListener('click',()=>{expanded=!expanded;renderCatalog();});
    renderCatalog();
    app.removeAttribute('aria-live');
  }

  fetch('../ies-distritales.json')
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(render)
    .catch(error => {
      console.error('Perfil institucional',error);
      app.innerHTML = `<main class="error shell"><div><span class="eyebrow">MaterIA Gris</span><h1>El perfil no pudo cargarse</h1><p>Los datos institucionales están temporalmente indisponibles. Puede volver al capítulo distrital o consultar el comprobante público.</p><div class="source-row" style="justify-content:center"><a href="../index.html#distrito">Volver al capítulo</a><a href="../ies-distritales.json">Abrir datos JSON</a></div></div></main>`;
    });
})();
