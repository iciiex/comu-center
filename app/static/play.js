(() => {
  'use strict';
  const body = document.body;
  const nav = document.getElementById('play-sidebar');
  const backdrop = document.querySelector('.nav-backdrop');
  let returnFocus = null;
  let toastTimeout;
  const number = new Intl.NumberFormat('fa-IR');
  const setNav = (open, trigger) => {
    if (!nav || !backdrop) return;
    body.classList.toggle('nav-open', open);
    backdrop.hidden = !open;
    document.querySelector('.mobile-menu')?.setAttribute('aria-expanded', String(open));
    if (open) {
      returnFocus = trigger;
      nav.querySelector('.close-sidebar').focus();
    } else {
      returnFocus?.focus();
    }
  };
  const toast = (message) => {
    let el = document.getElementById('live-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'live-toast'; el.className = 'toast'; el.setAttribute('role', 'status');
      body.append(el);
    }
    el.textContent = message;
    el.hidden = false;
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { el.hidden = true; }, 2800);
  };
  async function copy(value) {
    try {
      if (!navigator.clipboard) throw new Error('copy');
      await navigator.clipboard.writeText(value);
    } catch {
      const input = document.createElement('textarea');
      input.value = value;
      input.setAttribute('aria-label', 'متن برای کپی');
      body.append(input); input.select();
      const copied = document.execCommand('copy');
      input.remove();
      if (!copied) {
        window.prompt('برای کپی، متن زیر را بردارید:', value);
        return;
      }
    }
    toast('کپی شد.');
  }
  document.addEventListener('click', (evt) => {
    const button = evt.target.closest('button');
    if (!button) return;
    if (button.hasAttribute('data-nav-toggle')) setNav(!body.classList.contains('nav-open'), button);
    if (button.hasAttribute('data-dismiss')) button.closest('.flash').hidden = true;
    if (button.hasAttribute('data-go-back')) {
      if (history.length > 1) history.back(); else location.href = '/play/entrance';
    }
    if (button.hasAttribute('data-copy')) {
      const value = button.dataset.copy;
      copy(button.hasAttribute('data-full-url') ? new URL(value, location.origin).href : value);
    }
  });
  document.addEventListener('keydown', (evt) => {
    if (!body.classList.contains('nav-open')) return;
    if (evt.key === 'Escape') setNav(false);
    if (evt.key === 'Tab' && nav) {
      const focusable = Array.from(nav.querySelectorAll('a[href], button:not([disabled])'));
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (evt.shiftKey && document.activeElement === first) { evt.preventDefault(); last.focus(); }
      if (!evt.shiftKey && document.activeElement === last) { evt.preventDefault(); first.focus(); }
    }
  });
  matchMedia('(max-width: 830px)').addEventListener('change', (e) => {
    if (!e.matches && body.classList.contains('nav-open')) setNav(false);
  });
  document.addEventListener('submit', (evt) => {
    const form = evt.target;
    if (evt.defaultPrevented) return;
    const message = form.dataset.confirm;
    if ((message && !window.confirm(message)) || form.dataset.submitting) {
      evt.preventDefault();
      return;
    }
    if (form.method === 'post' && evt.submitter) {
      form.dataset.submitting = '1';
      evt.submitter.classList.add('is-submitting');
      evt.submitter.setAttribute('aria-busy', 'true');
    }
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[data-submitting]').forEach((form) => delete form.dataset.submitting);
    document.querySelectorAll('.is-submitting').forEach((button) => {
      button.classList.remove('is-submitting');
      button.removeAttribute('aria-busy');
    });
  });
  const balances = document.querySelectorAll('[data-balance]');
  if (!balances.length) return;
  const notices = document.querySelector('[data-notices]');
  const freshness = document.querySelector('[data-wallet-status]');
  const fields = document.querySelectorAll('[data-sales-value]');
  const table = document.querySelector('[data-pulse-table]');
  let pending = false, revision = table?.dataset.revision || '';
  function walletStatus(message = '') {
    if (!freshness) return;
    freshness.textContent = message;
    freshness.hidden = !message;
  }
  function updateTable(html) {
    if (!table || typeof html !== 'string') return;
    const open = new Set([...table.querySelectorAll('[data-tx-id][open]')].map(x => x.dataset.txId));
    const template = document.createElement('template');
    template.innerHTML = html; // Same-origin, autoescaped Jinja fragment.
    for (const details of template.content.querySelectorAll('[data-tx-id]')) {
      if (open.has(details.dataset.txId)) details.open = true;
    }
    table.replaceChildren(template.content);
  }
  async function pulse() {
    if (pending || document.hidden) return;
    pending = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    const params = new URLSearchParams();
    if (table) {
      params.set('view', table.dataset.pulseTable);
      if (revision) params.set('table_revision', revision);
      const tx = new URLSearchParams(location.search).get('tx');
      if (tx && table.dataset.pulseTable === 'wallet') params.set('tx', tx);
    }
    try {
      const response = await fetch(`/play/pulse?${params}`, {
        headers: { Accept: 'application/json' }, cache: 'no-store', signal: controller.signal,
      });
      if (!response.ok) {
        walletStatus(response.status === 401
          ? 'نشست شما پایان یافته است؛ این آخرین موجودی دریافت‌شده است.'
          : 'کیف به‌روز نشد؛ آخرین موجودی دریافت‌شده را می‌بینید.');
        return;
      }
      const state = await response.json();
      if (state.account !== freshness?.dataset.account) {
        walletStatus('حساب این صفحه تغییر کرده است؛ برای دیدن کیف حساب فعلی دوباره وارد شوید.');
        return;
      }
      if (!Number.isSafeInteger(state.balance) || state.balance < 0) throw new Error('Invalid balance');
      for (const node of balances) node.textContent = number.format(state.balance);
      for (const node of fields) {
        const value = state.sales?.[node.dataset.salesValue];
        if (Number.isSafeInteger(value)) node.textContent = number.format(value) + (node.dataset.suffix || '');
      }
      const meter = document.querySelector('.sales-meter');
      if (meter && Number.isSafeInteger(state.sales?.target_pct)) {
        meter.value = state.sales.target_pct;
        meter.textContent = number.format(meter.value) + '٪';
      }
      updateTable(state.table_html);
      revision = state.table_revision ?? '';
      notices?.classList.toggle('has-unread', state.unread > 0);
      walletStatus();
    } catch {
      walletStatus('کیف به‌روز نشد؛ آخرین موجودی دریافت‌شده را می‌بینید.');
    } finally {
      clearTimeout(timeout);
      pending = false;
    }
  }
  setInterval(pulse, 6500);
  window.addEventListener('focus', pulse);
  window.addEventListener('online', pulse);
  document.addEventListener('visibilitychange', pulse);
  document.addEventListener('play:wallet-changed', pulse);
  pulse();
})();
