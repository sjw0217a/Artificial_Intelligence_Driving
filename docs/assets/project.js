// Kokonut UI Typewriter의 타이핑 속도를 적용한다 (MIT).
async function typeHeroLead() {
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  if (reducedMotion.matches) return;

  const copy = document.querySelector('.lead-copy');
  const fullText = copy.textContent;
  const line = document.createElement('span');
  line.className = 'typewriter-line is-idle';
  line.setAttribute('aria-hidden', 'true');
  const text = document.createTextNode('');
  const caret = document.createElement('span');
  caret.className = 'typewriter-caret';

  line.append(text, caret);
  copy.after(line);
  copy.parentElement.classList.add('is-typing');

  const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  let idleTimer;
  function show(value) {
    text.data = value;
    line.classList.remove('is-idle');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => line.classList.add('is-idle'), 500);
  }
  await wait(200);
  let typed = '';
  for (const letter of fullText) {
    if (reducedMotion.matches) break;
    typed += letter;
    show(typed);
    const roll = Math.random();
    const delay = roll < .1 ? 100 : roll > .9 ? 25 : 30 + Math.random() * 40;
    await wait(typed.endsWith('...') ? 1000 : delay);
  }
  clearTimeout(idleTimer);
  line.remove();
  copy.parentElement.classList.remove('is-typing');
}
typeHeroLead();

const startCard = document.querySelector('.card.christmas');
const slot = document.querySelector('.scenario-slot');
const endCard = slot.querySelector('.card');
const detail = endCard.querySelector('.scenario-detail');
const preview = startCard.cloneNode(true);
preview.classList.add('morph-preview');
preview.setAttribute('aria-hidden', 'true');
preview.hidden = true;
endCard.append(preview);
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

const heading = document.querySelector('.scenario-heading');
const normalCard = document.querySelector('#scenario .compare > .card');
const siblings = [...startCard.parentElement.children].filter(card => card !== startCard);
const scatterDirections = [[-0.38, 0.72], [0.38, 0.9], [-0.19, 1.05]];

function phase(progress, from, to) {
  const t = Math.min(1, Math.max(0, (progress - from) / (to - from)));
  return t * t * (3 - 2 * t);
}

function updateScenario() {
  const start = startCard.getBoundingClientRect();
  const end = slot.getBoundingClientRect();
  const distance = end.top - start.top;
  const progress = (innerHeight * 0.42 - start.top) / Math.max(1, distance - innerHeight * 0.16);
  const phaseLength = 0.65;
  const exit = reducedMotion.matches ? 0 : phase(progress, 0, phaseLength);
  const enter = reducedMotion.matches ? 1 : phase(progress, 1 - phaseLength, 1);
  siblings.forEach((card, index) => {
    const [dx, dy] = scatterDirections[index];
    card.style.transform = exit ? `translate(${dx * innerWidth * exit}px, ${dy * distance * exit}px)` : '';
    card.style.opacity = exit ? 1 - exit : '';
  });

  heading.style.opacity = enter;
  heading.style.transform = enter < 1 ? `translateY(${(enter - 1) * innerHeight * 1.2}px)` : '';
  normalCard.style.opacity = enter;
  normalCard.style.transform = enter < 1 ? `translateX(${(enter - 1) * innerWidth}px)` : '';
  const moving = !reducedMotion.matches && progress > 0 && progress < 1;

  endCard.classList.toggle('is-morphing', moving);
  preview.hidden = !moving;
  startCard.style.opacity = !reducedMotion.matches && progress > 0 ? '0' : '';
  if (!moving) {
    endCard.style.transform = '';
    detail.style.opacity = '';
    detail.style.transform = '';
    endCard.style.opacity = !reducedMotion.matches && progress <= 0 ? '0' : '';
    return;
  }

  endCard.style.opacity = '';
  const t = phase(progress, 0, 1);
  const remaining = 1 - t;
  const sx = t + remaining * start.width / end.width;
  const sy = t + remaining * start.height / end.height;
  endCard.style.transform = `translate(${(start.left - end.left) * remaining}px, ${-distance * remaining}px) scale(${sx}, ${sy})`;
  preview.style.width = start.width + 'px';
  preview.style.height = start.height + 'px';
  preview.style.transform = `scale(${1 / sx}, ${1 / sy})`;
  preview.style.setProperty('--preview-blur', (8 * exit) + 'px');
  preview.style.opacity = 1 - exit;
  detail.style.opacity = enter;
  detail.style.transform = `scale(${1 / sx}, ${1 / sy})`;
}

let pending = false;
function scheduleUpdate() {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {
    pending = false;
    updateScenario();
  });
}
addEventListener('scroll', scheduleUpdate, {passive:true});
addEventListener('resize', scheduleUpdate);
addEventListener('load', scheduleUpdate);
reducedMotion.addEventListener('change', scheduleUpdate);
updateScenario();

for (const list of document.querySelectorAll('.tabs[role="tablist"]')) {
  const tabs = Array.from(list.querySelectorAll('[role="tab"]'));
  // 선택 밑줄: 탭 사이를 미끄러져 옮겨 간다
  const ink = document.createElement('span');
  ink.className = 'tab-ink';
  list.append(ink);
  list.classList.add('has-ink');
  function moveInk(tab) {
    ink.style.width = tab.offsetWidth + 'px';
    ink.style.transform = `translate(${tab.offsetLeft}px, ${tab.offsetTop + tab.offsetHeight - 2}px)`;
  }
  const panelOf = tab => document.getElementById(tab.getAttribute('aria-controls'));
  let current = null;
  function activate(selected, animate = true) {
    const previous = current && current !== selected ? panelOf(current) : null;
    const oldBars = previous ? [...previous.querySelectorAll('.r-bar i')].map(i => i.style.width) : [];
    const forward = current ? tabs.indexOf(selected) > tabs.indexOf(current) : true;
    for (const tab of tabs) {
      const active = tab === selected;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      const panel = panelOf(tab);
      panel.hidden = !active;
      const video = panel.querySelector('video');
      if (!video) continue;
      if (!active) video.pause();
      else if (!reducedMotion.matches) {
        video.currentTime = 0;
        video.play().catch(() => {});
      }
    }
    current = selected;
    moveInk(selected);
    if (!animate || !previous || reducedMotion.matches) return;
    // 새 패널은 고른 방향에서 살짝 밀려 들어온다
    const panel = panelOf(selected);
    panel.classList.remove('tab-enter-l', 'tab-enter-r');
    void panel.offsetWidth;
    panel.classList.add(forward ? 'tab-enter-r' : 'tab-enter-l');
    // 막대는 이전 패널의 같은 줄 길이에서 새 길이로 바뀐다
    panel.querySelectorAll('.r-bar i').forEach((bar, i) => {
      bar.dataset.width ??= bar.style.width;
      bar.style.transition = 'none';
      bar.style.width = oldBars[i] ?? '0%';
      void bar.offsetWidth;
      bar.style.transition = '';
      bar.style.width = bar.dataset.width;
    });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', event => {
      const offset = {ArrowLeft:-1, ArrowRight:1}[event.key];
      if (!offset) return;
      event.preventDefault();
      const next = tabs[(index + offset + tabs.length) % tabs.length];
      next.focus();
      activate(next);
    });
  });
  activate(tabs.find(tab => tab.getAttribute('aria-selected') === 'true'), false);
  addEventListener('resize', () => moveInk(current));
  addEventListener('load', () => moveInk(current));
  document.fonts?.ready.then(() => moveInk(current));
}

// 숫자 칸이 화면에 들어오면 0부터 올라간다. 끝난 뒤 글자는 원래와 똑같다.
for (const el of document.querySelectorAll('.stat .n:not(.tex)')) {
  const text = el.textContent;
  const m = text.match(/^([\d,]*\.?\d+)(.*)$/);
  if (!m || reducedMotion.matches) continue;
  const target = parseFloat(m[1].replace(/,/g, ''));
  if (!target) continue;
  const decimals = (m[1].split('.')[1] || '').length;
  const format = v => v.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals}) + m[2];
  el.setAttribute('aria-label', text);
  new IntersectionObserver((entries, observer) => {
    if (!entries[0].isIntersecting) return;
    observer.disconnect();
    const start = performance.now();
    let done = false;
    (function frame(now) {
      if (done) return;
      const t = Math.min(1, (now - start) / 1200);
      el.textContent = t < 1 ? format(target * (1 - (1 - t) ** 3)) : text;
      if (t < 1) requestAnimationFrame(frame);
    })(start);
    // 화면 갱신이 멈춘 탭에서도 원래 숫자로 끝나게
    setTimeout(() => { done = true; el.textContent = text; }, 1300);
  }, {threshold: 0.6}).observe(el);
  el.textContent = format(0);
}

// 도로 카드의 "결과 보기"를 누르면 결과 섹션의 같은 상황 탭을 연다.
for (const link of document.querySelectorAll('.to-result')) {
  link.addEventListener('click', () => document.getElementById(link.dataset.tab)?.click());
}
