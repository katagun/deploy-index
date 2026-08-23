(() => {
  const grid = document.querySelector('#provider-grid');
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll('.provider-card'));
  const search = document.querySelector('#catalog-search');
  const entity = document.querySelector('#filter-entity');
  const era = document.querySelector('#filter-era');
  const model = document.querySelector('#filter-model');
  const status = document.querySelector('#filter-status');
  const source = document.querySelector('#filter-source');
  const sort = document.querySelector('#sort-order');
  const count = document.querySelector('#result-count');
  const context = document.querySelector('#result-context');
  const empty = document.querySelector('#empty-state');
  const reset = document.querySelector('#reset-filters');
  const emptyReset = document.querySelector('#empty-reset');
  const categoryButtons = Array.from(document.querySelectorAll('[data-category]'));
  const viewButtons = Array.from(document.querySelectorAll('[data-view]'));
  let category = 'all';

  const normalize = (value) => String(value || '')
    .toLocaleLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9+.#/ -]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const params = new URLSearchParams(location.search);
  const setIfValid = (control, key) => {
    const value = params.get(key);
    if (value && Array.from(control.options).some((option) => option.value === value)) control.value = value;
  };
  if (params.get('q')) search.value = params.get('q');
  setIfValid(entity, 'type');
  setIfValid(era, 'era');
  setIfValid(model, 'model');
  setIfValid(status, 'status');
  setIfValid(source, 'source');
  setIfValid(sort, 'sort');
  if (params.get('category') && categoryButtons.some((button) => button.dataset.category === params.get('category'))) {
    category = params.get('category');
  }

  const setCategoryUI = () => {
    categoryButtons.forEach((button) => {
      const selected = button.dataset.category === category;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  };

  const matches = (card) => {
    const q = normalize(search.value);
    if (q) {
      const haystack = card.dataset.search || '';
      const tokens = q.split(' ').filter(Boolean);
      if (!tokens.every((token) => haystack.includes(token))) return false;
    }
    if (category !== 'all' && !(card.dataset.categories || '').split(',').includes(category)) return false;
    if (entity.value !== 'all' && card.dataset.entity !== entity.value) return false;
    if (era.value !== 'all' && card.dataset.era !== era.value) return false;
    if (model.value !== 'all' && !(card.dataset.models || '').split(',').includes(model.value)) return false;
    if (source.value === 'open' && card.dataset.openSource !== 'true') return false;
    if (source.value === 'proprietary' && card.dataset.openSource !== 'false') return false;
    if (status.value === 'available') {
      if (!['active', 'beta', 'transitioning'].includes(card.dataset.status)) return false;
    } else if (status.value !== 'all' && card.dataset.status !== status.value) {
      return false;
    }
    return true;
  };

  const comparators = {
    featured: (a, b) => Number(b.dataset.featured) - Number(a.dataset.featured) || a.dataset.name.localeCompare(b.dataset.name),
    name: (a, b) => a.dataset.name.localeCompare(b.dataset.name),
    newest: (a, b) => Number(b.dataset.launchYear || 0) - Number(a.dataset.launchYear || 0) || a.dataset.name.localeCompare(b.dataset.name),
    oldest: (a, b) => Number(a.dataset.launchYear || 9999) - Number(b.dataset.launchYear || 9999) || a.dataset.name.localeCompare(b.dataset.name),
  };

  const writeURL = () => {
    const next = new URLSearchParams();
    if (search.value.trim()) next.set('q', search.value.trim());
    if (category !== 'all') next.set('category', category);
    if (entity.value !== 'all') next.set('type', entity.value);
    if (era.value !== 'all') next.set('era', era.value);
    if (model.value !== 'all') next.set('model', model.value);
    if (status.value !== 'available') next.set('status', status.value);
    if (source.value !== 'all') next.set('source', source.value);
    if (sort.value !== 'featured') next.set('sort', sort.value);
    const query = next.toString();
    history.replaceState(null, '', query ? `${location.pathname}?${query}` : location.pathname);
  };

  const apply = () => {
    const ordered = [...cards].sort(comparators[sort.value] || comparators.featured);
    const fragment = document.createDocumentFragment();
    let visible = 0;
    ordered.forEach((card) => {
      const shown = matches(card);
      card.hidden = !shown;
      if (shown) visible += 1;
      fragment.appendChild(card);
    });
    grid.appendChild(fragment);
    count.textContent = visible.toLocaleString();
    empty.hidden = visible !== 0;
    grid.hidden = visible === 0;

    const pieces = [];
    if (category !== 'all') {
      const active = categoryButtons.find((button) => button.dataset.category === category);
      pieces.push(active ? active.dataset.label : category);
    }
    if (search.value.trim()) pieces.push(`matching “${search.value.trim()}”`);
    if (era.value !== 'all') pieces.push(`${era.options[era.selectedIndex].text.toLowerCase()}`);
    context.textContent = pieces.length ? pieces.join(' · ') : 'across the available catalog';
    setCategoryUI();
    writeURL();
  };

  let searchTimer;
  search.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(apply, 70);
  });
  [entity, era, model, status, source, sort].forEach((control) => control.addEventListener('change', apply));
  categoryButtons.forEach((button) => button.addEventListener('click', () => {
    category = button.dataset.category;
    apply();
  }));

  const resetAll = () => {
    search.value = '';
    category = 'all';
    entity.value = 'all';
    era.value = 'all';
    model.value = 'all';
    status.value = 'available';
    source.value = 'all';
    sort.value = 'featured';
    apply();
    search.focus({ preventScroll: false });
  };
  reset.addEventListener('click', resetAll);
  emptyReset.addEventListener('click', resetAll);

  viewButtons.forEach((button) => button.addEventListener('click', () => {
    const view = button.dataset.view;
    grid.classList.toggle('is-list', view === 'list');
    viewButtons.forEach((item) => {
      const selected = item === button;
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    localStorage.setItem('deployindex-view', view);
  }));
  const savedView = localStorage.getItem('deployindex-view');
  if (savedView === 'list') viewButtons.find((button) => button.dataset.view === 'list')?.click();

  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === 'Escape' && document.activeElement === search && search.value) {
      search.value = '';
      apply();
    }
  });

  apply();
})();
