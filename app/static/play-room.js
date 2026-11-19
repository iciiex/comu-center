(() => {
  'use strict';
  const root = document.getElementById('game-room');
  if (!root) return;
  const code = root.dataset.code;
  const csrf = document.querySelector('meta[name=csrf-token]').content;
  const stage = document.getElementById('game-stage');
  const side = document.getElementById('room-players');
  const settings = document.getElementById('room-settings');
  const connection = document.getElementById('room-connection');
  const alert = document.getElementById('room-alert');
  const sync = document.getElementById('room-sync');
  const format = new Intl.NumberFormat('fa-IR');
  const n = (value) => format.format(value);
  const e = (value) => String(value ?? '').replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const icon = (key) => `<svg class="p-icon" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><use href="/static/play-icons.svg#${e(key)}"></use></svg>`;
  const avatar = (key) => `<svg class="p-avatar" aria-hidden="true"><use href="/static/play-icons.svg#${e(key)}"></use></svg>`;
  const moves = {shir:'cards',quiz:'brain',words:'bolt'};
  const modes = {guess:'حدس کلمه',forbidden:'کلمات ممنوعه',speed:'چالش سرعت'};
  const difficulties = {easy:'آسان',medium:'متوسط',hard:'سخت'};
  const kinds = {customer:'مشتری',product:'محصول',feature:'ویژگی',limitation:'محدودیت',event:'اتفاق'};
  let state = null, stageSignature = '', playerSignature = '', settingSignature = '';
  let deadlineMs = null, busy = false, pendingPoll = false, moveEpoch = 0;
  let linkState = 'loading', uncertainMove = null;

  const timer = () => state.deadline ? `<span class="timer">${icon('clock')}<span id="game-timer">—</span></span>` : '';
  const title = (heading, detail) => `<div class="stage-head"><div><h2>${heading}</h2>${detail ? `<p>${detail}</p>` : ''}</div>${timer()}</div>`;
  const btn = (label, options = {}) => `<button class="btn ${options.style || 'btn-primary'}" type="submit" ${options.attrs || ''}>${options.icon ? icon(options.icon) : ''}${label}</button>`;
  const link = (href, label, style = 'btn-quiet') => `<a class="btn ${style}" href="${href}">${label}</a>`;
  const move = (name, body, extra = '') => `<form class="stage-form" method="post" action="/play/action" data-room-move><input type="hidden" name="action" value="room_move"><input type="hidden" name="move" value="${name}"><input type="hidden" name="phase_key" value="${e(state.phase_key)}"><input type="hidden" name="code" value="${e(code)}"><input type="hidden" name="move_seq" value="${e(state.move_seq)}"><input type="hidden" name="csrf" value="${e(csrf)}">${extra}${body}</form>`;
  const label = (who) => e(state.players.find((a) => a.id === who)?.name || 'بازیکن');
  const tag = (text, style) => `<span class="tag ${style}">${text}</span>`;
  const note = (text, kind = 'info') => `<div class="flash ${kind}">${icon(kind === 'error' ? 'info' : 'check')} ${text}</div>`;
  const me = () => state.players.find((p) => p.id === state.you);
  const mini = (cards, details = false) => `<div class="mini-cards">${cards.map((c) => `<span>${kinds[c.kind]}: <b>${e(c.label)}</b>${details ? ` · ${e(c.detail)}` : ''}</span>`).join('')}</div>`;
  const customer = () => state.customer ? `<div class="customer-card"><span>${icon('profile')} مشتری این دور</span><h3>${e(state.customer.label)}</h3><p>${e(state.customer.detail)}</p></div>` : '';
  const offer = (data) => `<article class="pitch-block"><h3>${label(data.player)}</h3><p>«${e(data.pitch)}»</p>${mini(data.cards)}</article>`;
  const join = () => `<form method="post" action="/play/action"><input type="hidden" name="csrf" value="${e(csrf)}"><input type="hidden" name="action" value="join_room"><input type="hidden" name="code" value="${e(code)}">${btn('پیوستن به اتاق', {icon:'arrow-left'})}</form>`;
  const invite = () => `/play/entrance?room=${encodeURIComponent(code)}`;
  function displayLobby() {
    if (!state.joined) {
      return title('به اتاق خانواده بپیوندید', 'به محض ورود، شما هم می‌توانید آماده شوید.') +
        `<div class="stage-lobby-art" style="background-image:url('/static/play-${state.game}.webp')"></div>` +
        (state.enabled && state.players.length < state.max ? join() : note('اتاق پر است یا بازی غیرفعال شده است.', 'error'));
    }
    const info = state.players.length < state.min ? `حداقل ${n(state.min)} بازیکن لازم است.` :
      state.players.length > state.max ? 'تعداد بازیکنان از ظرفیت تازهٔ بازی بیشتر است.' :
      'وقتی همه آماده باشند، میزبان بازی را آغاز می‌کند.';
    return title('لابی خانواده', `دور ${n(state.round)} · ${info}`) +
      `<div class="stage-lobby-art" style="background-image:url('/static/play-${state.game}.webp')"></div>` +
      `<p class="muted">هزینه هنگام شروع: ${n(state.cost * state.players.length)} توکن از کیف مشترک (${n(state.cost)} برای هر نفر).</p><div class="actions stage-actions">` +
      move('ready', btn(me()?.ready ? 'لغو آمادگی' : 'آماده‌ام!', {icon:'check',style:me()?.ready ? 'btn-quiet' : 'btn-primary'}),
        `<input type="hidden" name="value" value="${me()?.ready ? '0' : '1'}">`) +
      (state.host ? move('start', btn('آغاز بازی', {icon:'play',attrs:!state.can_start ? 'disabled' : ''})) : '') +
      move('leave', btn(state.host ? 'بستن اتاق' : 'خروج از اتاق', {style:'btn-quiet'})) + '</div>';
  }
  function displayBuild() {
    const choices = (key) => `<fieldset><legend>یک کارت ${kinds[key]} انتخاب کنید</legend>${state.hand.filter((a) => a.kind === key).map((c) => `<label class="pick-item"><input type="radio" name="${key}" value="${e(c.id)}" required><span><b>${e(c.label)}</b><small>${e(c.detail)}</small></span></label>`).join('')}</fieldset>`;
    return title('پیشنهادتان را بسازید', 'برای مشتری، یک محصول، یک ویژگی و یک معرفی کوتاه آماده کنید.') + customer() +
      (state.submitted.includes(state.you) ? note('پیشنهاد شما ثبت شد. منتظر بقیهٔ بازیکنان هستیم.') :
      move('offer', `<div class="pick-row">${choices('product')}${choices('feature')}</div>${mini(state.hand.filter((c) => ['event','limitation'].includes(c.kind)), true)}<div class="form-grid"><label class="wide"><span>متن معرفی پیشنهاد</span><textarea name="pitch" required minlength="6" maxlength="240" rows="3" placeholder="با این محصول، مشکل مشتری این‌طور حل می‌شود…"></textarea></label>${btn('ثبت پیشنهاد', {icon:'check'})}</div>`));
  }
  function displayVote() {
    return title('به بهترین پیشنهاد رأی بدهید', 'هر بازیکن فقط یک رأی دارد. پیشنهاد خودتان قابل انتخاب نیست.') +
      (state.voted ? note('رأی شما ثبت شد. نتیجه پس از پایان رأی‌گیری اعلام می‌شود.') : '') +
      state.offers.map((o) => offer(o) + (!state.voted && o.player !== state.you ? move('vote', btn('رأی به این پیشنهاد', {style:'btn-mint',icon:'star'}), `<input type="hidden" name="target" value="${e(o.player)}">`) : '')).join('');
  }
  function displayQuestion() {
    const Q = state.question;
    const answered = state.answered.includes(state.you);
    const options = Q.options.map((a, idx) => `<button class="btn btn-quiet ${answered && idx === state.my_answer ? 'picked' : ''}" name="option" type="submit" value="${idx}" ${answered ? 'disabled' : ''}><small>${n(idx + 1)}</small> ${e(a)}</button>`).join('');
    return title(`پرسش ${n(state.index + 1)} از ${n(state.count)}`, 'قبل از پایان زمان یک گزینه را انتخاب کنید.') +
      `<div class="question-block"><span>${e(Q.category)} · سطح ${e(Q.difficulty)}</span><h3>${e(Q.prompt)}</h3></div>` +
      move('answer', `<div class="options-grid">${options}</div>`) + (answered ? `<div class="block-gap">${note('پاسخ شما ثبت شد. منتظر سایر بازیکنان باشید.')}</div>` : '');
  }
  function displayClue() {
    return title(`نوبت ${n(state.index + 1)} از ${n(state.count)} · سرنخ`, `سرنخ را ${label(state.turn)} می‌سازد.`) +
      (state.secret_word ? `<div class="word-block"><span>فقط برای شما</span><h3>${e(state.secret_word)}</h3><p>این واژه‌ها ممنوع‌اند: ${state.forbidden.map(e).join('، ')}</p></div>` +
        move('clue', `<div class="form-grid"><label class="wide"><span>سرنخ بدون واژه‌های ممنوعه</span><input name="clue" required minlength="4" maxlength="120" autocomplete="off"></label>${btn('ثبت سرنخ', {icon:'check'})}</div>`) :
        note('بازیکن نوبت‌دار در حال نوشتن سرنخ است.'));
  }
  function displayGuess() {
    const detail = state.turn ? (state.may_guess ? 'نوبت شماست!' : `نوبت ${label(state.turn)}`) : 'هر کس زودتر پاسخ درست بدهد امتیاز می‌گیرد.';
    return title(`نوبت ${n(state.index + 1)} از ${n(state.count)} · واژه`, detail) +
      `<div class="word-block"><span>${e(state.category)}</span><h3>${e(state.hint)}</h3></div>` +
      (state.may_guess && state.attempts_left > 0 ? move('guess',`<div class="form-grid"><label class="wide"><span>حدس شما · ${n(state.attempts_left)} فرصت باقی‌مانده</span><input name="guess" maxlength="45" required autocomplete="off"></label>${btn('ثبت حدس', {icon:'bolt'})}</div>`) :
       note(state.may_guess ? 'فرصت‌های حدس این واژه را استفاده کردید.' : 'تا نوبت بعدی همراه بازیکنان بمانید.'));
  }
  function displayResult() {
    const { scores, winners, log, badges = [] } = state.result;
    const list = scores.map((s, i) => `<li><span>${n(i + 1)}</span>${avatar(s.avatar)}<strong>${e(s.name)}${winners.includes(s.id) ? ' ' + tag('برنده', 'gold') : ''}</strong>${s.votes !== undefined ? `<small>${n(s.votes)} رأی</small>` : ''}<b>${n(s.score)} امتیاز</b></li>`).join('');
    return `<div class="result-lead"><span class="result-medal">${icon('trophy')}</span><h2>${winners.length ? 'آفرین، قهرمان‌های خانواده!' : 'این دور بدون برنده پایان یافت'}</h2><p class="muted">نتیجهٔ دور ${n(state.round)} در تاریخچه ذخیره شد.</p></div><ul class="ranking-list result-ranks">${list}</ul>` +
      (badges.length ? `<div class="block-gap"><h3>${icon('medal')} نشان‌های تازه</h3><ul class="simple-list">${badges.map((award) => `<li><span class="symbol gold">${icon(award.icon)}</span><strong>${e(award.title)}</strong><small>${e(award.name)}</small></li>`).join('')}</ul></div>` : '') +
      (log.length ? `<details class="block-gap"><summary>مرور پاسخ‌ها</summary><ol class="steps">${log.map((a, i) => `<li><span>${n(i + 1)}</span>${e(a.prompt)} — ${e(a.answer)}</li>`).join('')}</ol></details>` : '') +
      `<div class="actions stage-actions">${state.host ? move('replay', btn('یک دور دیگر', {icon:'play'})) : ''}${link('/play/family/rooms', 'تاریخچهٔ بازی‌ها')}${link('/play/family/achievements?mine=1','نشان‌های من')}${link(`/play/family/game/${state.game}#game-leaderboard`,'جدول این بازی')}${link('/play/family/competitions','جدول رقابت')}</div>`;
  }
  function displayStage() {
    switch (state.phase) {
      case 'lobby': return displayLobby();
      case 'build': return displayBuild();
      case 'pitch': return title(`معرفی ${n(state.index + 1)} از ${n(state.count)}`, `نوبت معرفی ${label(state.speaker)} است.`) + offer(state.offer) +
        (state.speaker === state.you ? move('present', btn('پایان معرفی من', {icon:'arrow-left'})) : '<p class="muted">پیشنهاد بعدی در نوبت خودش نمایش داده می‌شود.</p>');
      case 'vote': return displayVote();
      case 'question': return displayQuestion();
      case 'clue': return displayClue();
      case 'guess': return displayGuess();
      case 'feedback': return title('پاسخ این نوبت', 'تا نوبت بعدی آماده بمانید.') +
        `<div class="question-block"><span>پاسخ درست</span><h3>${e(state.feedback.answer)}</h3><p>${state.feedback.correct.length ? state.feedback.correct.map(label).join('، ') + ' پاسخ درست داد.' : 'کسی پاسخ درست نداد.'}</p></div>` +
        (state.host ? move('next', btn(state.index + 1 === state.count ? 'دیدن نتیجه' : 'نوبت بعدی', {icon:'arrow-left'})) : '');
      case 'finished': return displayResult();
      default: return title('اتاق بسته شده است', 'برای بازی دوباره اتاق دیگری را باز کنید.') + link('/play/family/rooms','بازگشت به اتاق‌ها');
    }
  }
  function renderPlayers() {
    const list = state.players.map((player) => {
      const self = player.id === state.you;
      let status = '';
      if (state.phase === 'lobby') status = tag(player.ready ? 'آماده' : 'منتظر', player.ready ? 'mint' : 'gray');
      else if (state.phase === 'pitch' && state.speaker === player.id) status = tag('در حال معرفی','gold');
      else if (state.phase === 'build' && state.submitted.includes(player.id)) status = tag('ثبت کرد','mint');
      else if (state.phase === 'vote' && state.votes_cast.includes(player.id)) status = tag('رأی داد','mint');
      else if (state.phase === 'question' && state.answered.includes(player.id)) status = tag('پاسخ داد','mint');
      else if (state.turn === player.id) status = tag('نوبت بازی','gold');
      else if (['quiz','words'].includes(state.game)) status = tag(n(player.score) + ' امتیاز','gray');
      return `<li>${avatar(player.avatar)}<div><strong>${e(player.name)}${self ? ' (شما)' : ''}</strong><small>${player.id === state.host_id ? 'میزبان' : 'بازیکن'} · ${player.age === 'child' ? 'کودک' : 'بزرگسال'}</small></div>${status}</li>`;
    }).join('');
    return `<h2>${icon('users')} بازیکنان · ${n(state.players.length)} از ${n(state.max)}</h2><ul class="player-list">${list}</ul>`;
  }
  function renderRoomSettings() {
    const mode = modes[state.options.mode];
    const option = state.game === 'quiz' ? `${e(state.options.category || 'همهٔ موضوع‌ها')}، ${e(difficulties[state.options.difficulty] || 'ترکیبی')}` : mode;
    return `<h2>${icon(moves[state.game])} ${option || 'اتاق خانوادگی'}</h2>` +
      (state.phase === 'lobby' && state.joined && !state.role_is_child ? `<div class="invite-room"><p>لینک را برای اعضای خانواده بفرستید. هر نفر در یک دستگاه یا نمایهٔ جدا وارد شود.</p><div class="actions"><button class="btn btn-small btn-mint" type="button" data-copy="${invite()}" data-full-url>${icon('copy')} کپی لینک دعوت</button><button type="button" class="btn btn-small btn-quiet" data-copy="${e(code)}">کپی کد</button></div></div>` : '') +
      `<a class="text-link room-summary" href="/play/family/game/${state.game}#rules">راهنمای بازی ${icon('arrow-left')}</a>`;
  }
  function showAlert(message) {
    alert.textContent = message;
    alert.hidden = !message;
  }
  function update(data) {
    if (typeof data?.phase_key !== 'string' || !Number.isSafeInteger(data.move_seq)) {
      throw new Error('Invalid room state');
    }
    if (state && data.you !== state.you) {
      endConnection(401, 'حساب این اتاق تغییر کرده است؛ دوباره وارد شوید.');
      return false;
    }
    if (state && data.rev < state.rev) return false;
    const changed = state && state.phase_key !== data.phase_key;
    const balanceChanged = state?.phase === 'lobby' && data.phase !== 'lobby';
    const oldPhase = state?.phase;
    state = data;
    deadlineMs = state.deadline ? performance.now() + (state.deadline - state.now) * 1000 : null;
    if (changed) { showAlert(''); showSync(''); }
    const signature = [state.phase_key, state.move_seq, state.you, state.joined, state.host, state.answered?.includes(state.you), state.submitted?.includes(state.you), state.voted, state.attempts_left,
      ...(state.phase === 'lobby' ? [state.can_start, state.players.length, me()?.ready, state.min, state.max, state.cost, state.enabled] : [])].join('|');
    if (signature !== stageSignature) {
      stageSignature = signature;
      const hasFocus = stage.contains(document.activeElement);
      stage.classList.toggle('result-panel', state.phase === 'finished');
      stage.innerHTML = displayStage();
      if (changed && oldPhase && hasFocus) {
        const heading = stage.querySelector('h2');
        if (heading) { heading.tabIndex = -1; heading.focus({preventScroll:true}); }
      }
    }
    const players = renderPlayers();
    if (players !== playerSignature) { side.innerHTML = players; playerSignature = players; }
    const info = renderRoomSettings();
    if (info !== settingSignature) { settings.innerHTML = info; settingSignature = info; }
    updateTimer();
    if (balanceChanged) document.dispatchEvent(new Event('play:wallet-changed'));
    return true;
  }
  function updateTimer() {
    const element = document.getElementById('game-timer');
    if (!element || deadlineMs === null) return;
    const seconds = Math.max(0, Math.ceil((deadlineMs - performance.now()) / 1000));
    element.textContent = `${n(seconds)} ثانیه`;
    element.parentElement.classList.toggle('urgent', seconds <= 8);
  }
  function showSync(message, kind = 'info') {
    sync.textContent = message;
    sync.className = `flash ${kind}`;
    sync.hidden = !message;
  }
  function connectionState(next) {
    linkState = next;
    const labels = {
      online:'همگام با اتاق', offline:'ارتباط قطع است؛ تلاش دوباره…', closed:'دسترسی به اتاق قطع شد',
    };
    connection.classList.toggle('disconnected', next !== 'online');
    connection.innerHTML = `<i></i> ${labels[next]}`;
    for (const form of stage.querySelectorAll('[data-room-move]')) form.inert = next !== 'online';
  }
  function endConnection(status, error) {
    connectionState('closed');
    showSync('');
    showAlert(error || 'دسترسی به این اتاق ممکن نیست.');
    if (status === 401) {
      const a = document.createElement('a');
      a.className = 'text-link'; a.href = invite(); a.textContent = 'ورود دوباره';
      alert.append(' ', a);
    }
  }
  function recovered(data) {
    if (!update(data)) return;
    const reconnected = linkState === 'offline';
    connectionState('online');
    if (reconnected) {
      const canRetry = uncertainMove?.phase === data.phase_key && uncertainMove.seq === data.move_seq;
      showSync(canRetry
        ? 'اتصال دوباره برقرار شد؛ می‌توانید حرکت را دوباره ارسال کنید.'
        : 'اتصال دوباره برقرار شد؛ وضعیت اتاق به‌روز است.', 'success');
    }
    uncertainMove = null;
  }
  function lostConnection() {
    connectionState('offline');
    showSync(uncertainMove
      ? 'تأیید حرکت دریافت نشد؛ پس از اتصال، وضعیت ثبت‌شده بررسی می‌شود.'
      : 'ارتباط با اتاق قطع است؛ آخرین وضعیت دریافت‌شده را می‌بینید.');
  }
  async function request(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5500);
    try {
      const response = await fetch(url, {
        ...options, headers:{Accept:'application/json'}, cache:'no-store', signal:controller.signal,
      });
      if (response.status >= 500) throw new Error('Room unavailable');
      return [response, await response.json()];
    } finally { clearTimeout(timeout); }
  }
  async function poll() {
    if (linkState === 'closed' || pendingPoll || busy || document.hidden) return;
    pendingPoll = true;
    const epoch = moveEpoch;
    try {
      const [response, data] = await request(`/play/state/${encodeURIComponent(code)}`);
      if (epoch !== moveEpoch) return; // A poll started before a move must not overwrite its result.
      if ([401,403,404].includes(response.status)) endConnection(response.status, data.error);
      else if (response.ok) recovered(data);
      else lostConnection();
    } catch {
      if (epoch === moveEpoch) lostConnection();
    } finally { pendingPoll = false; }
  }
  stage.addEventListener('submit', async (ev) => {
    const form = ev.target;
    if (!form.hasAttribute('data-room-move')) return;
    ev.preventDefault();
    if (busy || linkState !== 'online') return;
    const moveName = form.elements.move.value;
    if (moveName === 'leave' && state.host && !window.confirm('این اتاق برای همه بسته شود؟')) return;
    busy = true;
    moveEpoch += 1;
    showAlert('');
    showSync('');
    const params = new URLSearchParams(new FormData(form));
    const submitter = ev.submitter;
    if (submitter?.name) params.set(submitter.name, submitter.value);
    if (submitter) submitter.disabled = true;
    try {
      const [response, data] = await request('/play/action', {method:'POST', body:params});
      if (response.status === 401) endConnection(401, data.error);
      else if (!response.ok) showAlert(data.error || 'این حرکت ثبت نشد.');
      else {
        recovered(data);
        if (linkState !== 'closed' && moveName === 'guess' && data.phase === 'guess') {
          showAlert('این واژه درست نیست؛ می‌توانید دوباره حدس بزنید.');
          stage.querySelector('input[name=guess]')?.focus();
        }
      }
    } catch {
      uncertainMove = {phase: params.get('phase_key'), seq: Number(params.get('move_seq'))};
      lostConnection();
    } finally {
      busy = false;
      if (submitter?.isConnected) submitter.disabled = false;
      poll();
    }
  });
  const initial = document.getElementById('room-initial');
  try { recovered(JSON.parse(initial.content.textContent)); }
  catch { lostConnection(); }
  poll();
  window.setInterval(poll, 1400);
  window.setInterval(updateTimer, 180);
  window.addEventListener('online', poll);
  document.addEventListener('visibilitychange', poll);
})();
